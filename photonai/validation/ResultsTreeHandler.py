import itertools
import pickle
import numpy as np
import pandas as pd
import seaborn as sns
import csv
import os
import matplotlib.pyplot as plt

from scipy.stats import sem
from sklearn.metrics import confusion_matrix, roc_curve
from pymodm import connect
from pymongo import DESCENDING
from pymongo.errors import DocumentTooLarge
from typing import Union
from prettytable import PrettyTable
import pprint

from ..validation.ResultsDatabase import MDBHyperpipe
from ..validation.Validate import Scorer
from ..base.Helper import PHOTONDataHelper
from ..photonlogger.Logger import Logger


class ResultsTreeHandler:
    def __init__(self, result_tree: MDBHyperpipe = None, output_settings = None):
        self.results = result_tree
        self.save_settings = output_settings

    def load_from_file(self, results_file: str):
        self.results = MDBHyperpipe.from_document(pickle.load(open(results_file, 'rb')))

    def load_from_mongodb(self, mongodb_connect_url: str, pipe_name: str):
        connect(mongodb_connect_url)
        results = list(MDBHyperpipe.objects.raw({'name': pipe_name}))
        if len(results) == 1:
            self.results = results[0]
        elif len(results) > 1:
            self.results = MDBHyperpipe.objects.order_by([("time_of_results", DESCENDING)]).raw({'name': pipe_name}).first()
            Logger().warn('Found multiple hyperpipes with that name. Returning most recent one.')
        else:
            raise FileNotFoundError('Could not load hyperpipe from MongoDB.')

    @staticmethod
    def get_methods():
        """
        This function returns a list of all methods available for ResultsTreeHandler.
        """
        methods_list = [s for s in dir(ResultsTreeHandler) if not '__' in s]
        return methods_list

    def get_performance_table(self):
        """
        This function returns a summary table of the overall results.
        ToDo: add best_config information!
        """

        res_tab = pd.DataFrame()
        for i, folds in enumerate(self.results.outer_folds):
            # add best config infos
            try:
                res_tab.loc[i, 'best_config'] = folds.best_config.human_readable_config
            except:
                res_tab.loc[i, 'best_config'] = str(folds.best_config.human_readable_config)

            # add fold index
            res_tab.loc[i, 'fold'] = folds.fold_nr

            # add sample size infos
            res_tab.loc[i, 'n_train'] = folds.best_config.inner_folds[0].number_samples_training
            res_tab.loc[i, 'n_validation'] = folds.best_config.inner_folds[0].number_samples_validation

            # add performance metrics
            d = folds.best_config.inner_folds[0].validation.metrics
            for key, value in d.items():
                res_tab.loc[i, key] = value

        # add row with overall info
        res_tab.loc[i + 1, 'n_validation'] = np.sum(res_tab['n_validation'])
        for key, value in d.items():
            m = res_tab.loc[:, key]
            res_tab.loc[i+1, key] = np.mean(m)
            res_tab.loc[i + 1, key + '_sem'] = sem(m)   # standard error of the mean
        res_tab.loc[i + 1, 'best_config'] = 'Overall'
        return res_tab

    def get_performance_outer_folds(self):
        performances = dict()
        for metric in self.results.outer_folds[0].best_config.inner_folds[0].validation.metrics.keys():
            performances[metric] = list()
        for i, fold in enumerate(self.results.outer_folds):
            for metric, value in fold.best_config.inner_folds[0].validation.metrics.items():
                performances[metric].append(value)
        return performances

    def get_config_evaluations(self):
        """
        Return the test performance of every tested configuration in every outer fold.
        :return:
        """
        config_performances = list()
        maximum_fold = None
        for outer_fold in self.results.outer_folds:
            if maximum_fold is None or len(outer_fold.tested_config_list) > maximum_fold:
                maximum_fold = len(outer_fold.tested_config_list)

        for outer_fold in self.results.outer_folds:
            performance = dict()
            for metric in self.results.metrics:
                performance[metric] = list()

            for i in range(maximum_fold):
                #for config in outer_fold.tested_config_list:
                for metric in self.results.metrics:
                    if i >= len(outer_fold.tested_config_list):
                        performance[metric].append(np.nan)
                        continue
                    config = outer_fold.tested_config_list[i]
                    if config.config_failed:
                        performance[metric].append(np.nan)
                    else:
                        for item in config.metrics_test:
                            if (item.operation == 'FoldOperations.MEAN') and (item.metric_name == metric):
                                performance[metric].append(item.value)
            config_performances.append(performance)

        config_performances_dict = dict()
        for metric in self.results.metrics:
            config_performances_dict[metric] = list()
            for fold in config_performances:
                config_performances_dict[metric].append(fold[metric])

        return config_performances_dict

    def get_minimum_config_evaluations(self):
        config_evaluations = self.get_config_evaluations()
        minimum_config_evaluations = dict()

        for metric, evaluations in config_evaluations.items():
            minimum_config_evaluations[metric] = list()
            greater_is_better = Scorer.greater_is_better_distinction(metric)

            for fold in evaluations:
                fold_evaluations = list()

                if greater_is_better:
                    for i, config in enumerate(fold):
                        if i == 0:
                            last_config = config
                        else:
                            if config > last_config:
                                last_config = config
                        fold_evaluations.append(last_config)
                else:
                    last_config = np.inf
                    for i, config in enumerate(fold):
                        if i == 0:
                            last_config = config
                        else:
                            if config < last_config:
                                last_config = config
                        fold_evaluations.append(last_config)
                minimum_config_evaluations[metric].append(fold_evaluations)

        return minimum_config_evaluations

    def plot_optimizer_history(self, metric,
                               title: str = 'Optimizer History',
                               type: str = 'plot',
                               reduce_scatter_by: Union[int, str] = 'auto',
                               file: str = None):
        """
        :param metric: specify metric that has been stored within the PHOTON results tree
        :param type: 'plot' or 'scatter'
        :param reduce_scatter_by: integer or string ('auto'), reduce the number of points plotted by scatter
        :param file: specify a filename if you want to save the plot
        :return:
        """

        if metric not in self.results.metrics:
            raise ValueError('Metric "{}" not stored in results tree'.format(metric))

        config_evaluations = self.get_config_evaluations()
        minimum_config_evaluations = self.get_minimum_config_evaluations()

        # handle different lengths
        min_corresponding = len(min(config_evaluations[metric], key=len))
        config_evaluations_corres = [configs[:min_corresponding] for configs in config_evaluations[metric]]
        minimum_config_evaluations_corres = [configs[:min_corresponding] for configs in minimum_config_evaluations[metric]]

        mean = np.nanmean(np.asarray(config_evaluations_corres), axis=0)
        mean_min = np.nanmean(np.asarray(minimum_config_evaluations_corres), axis=0)

        greater_is_better = Scorer.greater_is_better_distinction(metric)
        if greater_is_better:
            caption = 'Maximum'
        else:
            caption = 'Minimum'

        plt.figure()
        if type == 'plot':
            plt.plot(np.arange(0, len(mean)), mean, '-', color='gray', label='Mean Performance')

        elif type == 'scatter':
            # now do smoothing
            if isinstance(reduce_scatter_by, str):
                if reduce_scatter_by != 'auto':
                    Logger().warn('{} is not a valid smoothing_kernel specifier. Falling back to "auto".'.format(
                        reduce_scatter_by))

                # if auto, then calculate size of reduce_scatter_by so that 75 points on x remain
                # smallest reduce_scatter_by should be 1
                reduce_scatter_by = max([np.floor(min_corresponding / 75).astype(int), 1])

            if reduce_scatter_by > 1:
                plt.plot([], [], ' ', label="scatter reduced by factor {}".format(reduce_scatter_by))

            for i, fold in enumerate(config_evaluations[metric]):
                # add a few None so that list can be divided by smoothing_kernel
                remaining = len(fold) % reduce_scatter_by
                if remaining:
                    fold.extend([np.nan] * (reduce_scatter_by - remaining))
                # calculate mean over every n elements so that plot is less cluttered
                reduced_fold = np.nanmean(np.asarray(fold).reshape(-1, reduce_scatter_by), axis=1)
                reduced_xfit = np.arange(reduce_scatter_by / 2, len(fold), step=reduce_scatter_by)
                if i == len(config_evaluations[metric])-1:
                    plt.scatter(reduced_xfit, np.asarray(reduced_fold), color='gray', alpha=0.5, label='Performance', marker='.')
                else:
                    plt.scatter(reduced_xfit, np.asarray(reduced_fold), color='gray', alpha=0.5, marker='.')
        else:
            raise ValueError('Please specify either "plot" or "scatter".')

        plt.plot(np.arange(0, len(mean_min)), mean_min, '-', color='black', label='Mean {} Performance'.format(caption))

        for i, fold in enumerate(minimum_config_evaluations[metric]):
            xfit = np.arange(0, len(fold))
            plt.plot(xfit, fold, '-', color='black', alpha=0.5)

        plt.ylabel(metric.replace('_', ' '))
        plt.xlabel('No of Evaluations')

        plt.legend()
        plt.title(title)
        if file:
            plt.savefig(file)
        else:
            if self.save_settings:
                file = os.path.join(self.save_settings.results_folder, "optimizer_history.png")
                plt.savefig(file)

        plt.show()

    def get_val_preds(self, sort_CV=True):
        """
        This function returns the predictions, true targets, and fold index
        for the best configuration of each outer fold.
        """
        y_true = []
        y_pred = []
        sample_inds = []
        y_pred_probabilities = []
        fold_idx = []
        for i, fold in enumerate(self.results.outer_folds):
            n_samples = len(fold.best_config.inner_folds[0].validation.y_true)
            y_true.extend(fold.best_config.inner_folds[0].validation.y_true)
            y_pred.extend(fold.best_config.inner_folds[0].validation.y_pred)
            y_pred_probabilities.extend(fold.best_config.inner_folds[0].validation.probabilities)
            fold_idx.extend(np.repeat(i, n_samples))
            if sort_CV:
                sample_inds.extend(fold.best_config.inner_folds[0].validation.indices)
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        y_pred_probabilities = np.asarray(y_pred_probabilities)
        fold_idx = np.asarray(fold_idx)
        if sort_CV:
            sample_inds = np.asarray(sample_inds)
            sort_index = np.argsort(sample_inds)
            y_true = y_true[sort_index]
            y_pred = y_pred[sort_index]
            if len(y_pred_probabilities) != 0:
                y_pred_probabilities = y_pred_probabilities[sort_index]

        return {'y_true': y_true, 'y_pred': y_pred, 'sample_inds_CV': sample_inds,
                'y_pred_probabilities': y_pred_probabilities, 'fold_indices': fold_idx}

    def get_inner_val_preds(self, sort_CV=True, config_no=0):
        """
        This function returns the predictions, true targets, and fold index
        for the best configuration of each inner fold if outer fold is not set and eval_final_performance is False
        AND there is only 1 config tested!
        :param sort_CV: sort predictions to match input sequence (i.e. undo CV shuffle = True)?
        :param config_no: which tested config to use?
        """
        y_true = []
        y_pred = []
        if sort_CV:
            sample_inds = []
        y_pred_probabilities = []
        fold_idx = []
        for i, fold in enumerate(self.results._data['outer_folds'][0]['tested_config_list'][config_no]['inner_folds']):
            n_samples = len(fold['validation']['y_true'])
            y_true.extend(fold['validation']['y_true'])
            y_pred.extend(fold['validation']['y_pred'])
            y_pred_probabilities.extend(fold['validation']['probabilities'])
            fold_idx.extend(np.repeat(i, n_samples))
            if sort_CV:
                sample_inds.extend(fold['validation']['indices'])
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        y_pred_probabilities = np.asarray(y_pred_probabilities)
        fold_idx = np.asarray(fold_idx)
        if sort_CV:
            sample_inds = np.asarray(sample_inds)
            sort_index = np.argsort(sample_inds)
            y_true = y_true[sort_index]
            y_pred = y_pred[sort_index]
            if len(y_pred_probabilities) != 0:
                y_pred_probabilities = y_pred_probabilities[sort_index]

        return {'y_true': y_true, 'y_pred': y_pred,
                'y_pred_probabilities': y_pred_probabilities, 'fold_indices': fold_idx}

    def get_importance_scores(self):
        """
        This function returns the importance scores for the best configuration of each outer fold.
        """
        imps = []
        for i, fold in enumerate(self.results.outer_folds):
            imps.append(fold.best_config.inner_folds[0].training.feature_importances)
        return imps

    def plot_true_pred(self, confidence_interval=95):
        """
        This function plots predictions vs. (true) targets and plots a regression line
        with confidence interval.
        """
        preds = ResultsTreeHandler.get_val_preds(self)
        ax = sns.regplot(x=preds['y_pred'], y=preds['y_true'], ci=confidence_interval)
        ax.set(xlabel='Predicted Values', ylabel='True Values')
        plt.show()

    def plot_confusion_matrix(self, classes=None, normalize=False, title='Confusion matrix'):
        """
        This function prints and plots the confusion matrix.
        Normalization can be applied by setting `normalize=True`.
        """

        preds = ResultsTreeHandler.get_val_preds(self)
        cm = confusion_matrix(preds['y_true'], preds['y_pred'])
        np.set_printoptions(precision=2)
        if normalize:
            cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
            Logger().info("Normalized confusion matrix")
        else:
            Logger().info('Confusion matrix')
        Logger().info(cm)

        plt.figure()
        cmap = plt.cm.Blues
        plt.imshow(cm, interpolation='nearest', cmap=cmap)
        plt.title(title)
        plt.colorbar()

        if classes == None:
            classes = ['class ' + str(c + 1) for c in np.unique(preds['y_true'])]
        tick_marks = np.arange(len(classes))
        plt.xticks(tick_marks, classes, rotation=45)
        plt.yticks(tick_marks, classes)

        fmt = '.2f' if normalize else 'd'
        thresh = cm.max() / 2.
        for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
            plt.text(j, i, format(cm[i, j], fmt),
                     horizontalalignment="center",
                     color="white" if cm[i, j] > thresh else "black")

        plt.tight_layout()
        plt.ylabel('True label')
        plt.xlabel('Predicted label')
        #plotlyFig = ResultsTreeHandler.__plotlyfy(plt)
        plt.show()

    def plot_roc_curve(self, pos_label=1, y_score_col=1):
        """
        This function plots the ROC curve.
        :param pos_label: In binary classiciation, what is the positive class label?
        :param y_score_col: In binary classiciation, which column of the probability matrix contains the positive class probabilities?
        :return: None
        """


        # get predictive probabilities
        preds = ResultsTreeHandler.get_val_preds(self)

        # get ROC infos
        fpr, tpr, _ = roc_curve(y_true=preds['y_true'],
                                y_score=preds['y_pred_probabilities'][:, y_score_col],
                                pos_label=pos_label)

        # plot ROC curve
        plt.figure()
        plt.plot([0, 1], [0, 1], 'k--')
        plt.plot(fpr, tpr)
        plt.xlabel('False positive rate')
        plt.ylabel('True positive rate')
        plt.title('Receiver Operating Characteristic (ROC) Curve')
        plt.legend(loc='best')
        plt.show()

    def eval_mean_time_components(self):
        """
            This function create charts and tables out of the time-monitoring.
            :param result_path: path of saving .csv and pie.png in.
            :return: None
        """

        # save how long the element took per config and in total
        result_dict = {}
        caching = False
        default_dict = {'total_seconds': 0,
                        'total_items_processed': 0,
                        'mean_seconds_per_config': 0,
                        'mean_seconds_per_item': 0}
        for outer_fold in self.results.outer_folds:
            for config_nr, config in enumerate(outer_fold.tested_config_list):
                tmp_config_dict = {}
                # resort time entries for each element so that is has the following structure
                # element_name -> fit/transform/predict -> (seconds, nr_items)
                for inner_fold in config.inner_folds:
                    for time_key, time_values in inner_fold.time_monitor.items():
                        for value_item in time_values:
                            name, time, nr_items = value_item[0], value_item[1], value_item[2]
                            if name not in tmp_config_dict:
                                tmp_config_dict[name] = {}
                            if time_key not in tmp_config_dict[name]:
                                tmp_config_dict[name][time_key] = []
                            tmp_config_dict[name][time_key].append((time, nr_items))

                # calculate mean time per config and absolute time
                for element_name, element_time_dict in tmp_config_dict.items():
                    for element_time_key, element_time_list in element_time_dict.items():
                        if element_time_key == "transform_cached":
                            caching = True
                        mean_time = np.mean([i[0] for i in element_time_list])
                        total_time = np.sum([i[0] for i in element_time_list])
                        total_items_processed = np.sum([i[1] for i in element_time_list])

                        if element_name not in result_dict:
                            result_dict[element_name] = {}
                        if element_time_key not in result_dict[element_name]:
                            result_dict[element_name][element_time_key] = dict(default_dict)

                        result_dict[element_name][element_time_key]['total_seconds'] += total_time
                        result_dict[element_name][element_time_key]['total_items_processed'] += total_items_processed
                        mean_time_per_config = result_dict[element_name][element_time_key]['mean_seconds_per_config']
                        tmp_total_mean = ((mean_time_per_config * config_nr) + mean_time) / (config_nr + 1)
                        result_dict[element_name][element_time_key]['mean_seconds_per_config'] = tmp_total_mean
                        tmp_mean_per_item = result_dict[element_name][element_time_key]['total_seconds'] / \
                                            result_dict[element_name][element_time_key]['total_items_processed']
                        result_dict[element_name][element_time_key]['mean_seconds_per_item'] = tmp_mean_per_item

        format_str = '{:06.6f}'
        if caching:
            # add transform_cached and transform_computed values to transform_total
            for name, sub_result_dict in result_dict.items():
                if "transform_cached" in sub_result_dict:
                    result_dict[name]["transform"] = dict(default_dict)
                    for value_dict in sub_result_dict.values():
                        for info in value_dict.keys():
                            result_dict[name]["transform"][info] = result_dict[name]["transform_cached"][info]
                            # in case everything's been in the cache we have no computation
                            if "transform_computed" in sub_result_dict:
                                result_dict[name]["transform"][info] += result_dict[name]["transform_computed"][info]
                    if "transform_computed" in sub_result_dict:
                        # calculate a ratio, if caching was helpful and how much of the time it saved
                        result_dict[name]["cache_ratio"] = result_dict[name]["transform_cached"]["total_seconds"]/result_dict[name]["transform_computed"]["total_seconds"]

            csv_keys = ["fit", "transform", "transform_computed", "transform_cached", "predict"]
            csv_titles = csv_keys
            plot_list = ["fit", "transform"]
            method_list = ["fit", "transform_computed", "transform_cached", "predict"]
        else:
            csv_keys = ["fit", "transform_computed", "predict"]
            csv_titles = ["fit", "transform", "predict"]
            plot_list = ["fit", "transform_computed"]
            method_list = ["fit", "transform_computed", "predict"]
        sub_keys = ["total_seconds", "mean_seconds_per_config", "mean_seconds_per_item"]
        csv_filename = os.path.join(self.save_settings.results_folder, 'time_monitor.csv')
        with open(csv_filename, 'w') as csvfile:
            writer = csv.writer(csvfile)
            header1 = [""]
            for k_name in csv_titles:
                header1.extend([k_name, "", ""])
            header2 = ["Element"] + (sub_keys * len(csv_titles))
            if caching:
                header1.append("")
                header2.append("cache_ratio")
            writer.writerow(header1)
            writer.writerow(header2)
            for item, item_dict in result_dict.items():
                row = [item]
                for time_key in csv_keys:
                    for sub_key in sub_keys:
                        if time_key in item_dict:
                            row.append(format_str.format(item_dict[time_key][sub_key]))
                        else:
                            row.append('')
                if caching:
                    if "cache_ratio" in item_dict:
                        row.append(item_dict["cache_ratio"])
                writer.writerow(row)

        debug = True

        # dataList = [sizes_fit, sizes_transComp, sizes_transCache, sizes_trans, sizes_predict]
        # titleList = ["fit", "transform computed", "transform cached", "transform total", "predict"]
        #
        #
        fig = plt.figure(figsize=(18, 10), dpi=160)
        for i, k in enumerate(plot_list):
            ax1 = fig.add_subplot(231+i)
            data = [element[k]["total_seconds"] for name, element in result_dict.items() if k in element]
            patches, _ = plt.pie(data, shadow=True, startangle=90, pctdistance=0.7) #utopct=self.eval_mean_time_Autopct,
            plt.legend(patches, [name for name, element in result_dict.items() if k in element], loc="best")
            plt.axis('equal')
            plt.tight_layout()
            plt.title(csv_titles[i])

        # add another plot for all methods
        ax1 = fig.add_subplot(231 + len(plot_list))
        data = []
        for k in method_list:
            data.append(np.sum([element[k]["total_seconds"] for name, element in result_dict.items() if k in element]))
        patches, _ = plt.pie(data, shadow=True, startangle=90, pctdistance=0.7)  # utopct=self.eval_mean_time_Autopct,
        plt.legend(patches, method_list, loc="best")
        plt.axis('equal')
        plt.tight_layout()
        plt.title("methods")

        plt.savefig(os.path.join(self.save_settings.results_folder, 'time_monitor_pie.png'))

    def save(self):

        if self.save_settings.mongodb_connect_url:
            connect(self.save_settings.mongodb_connect_url, alias='photon_core')
            Logger().debug('Write results to mongodb...')
            try:
                self.results.save()
            except DocumentTooLarge as e:
                Logger().error('Could not save document into MongoDB: Document too large')
                # try to reduce the amount of configs saved
                # if len(results_tree.outer_folds[0].tested_config_list) > 100:
                #     for outer_fold in results_tree.outer_folds:
                #         metrics_configs = [outer_fold.tested_configlist

        if self.save_settings.save_output:
            self.write_result_tree_to_file()
            self.write_summary()
            self.eval_mean_time_components()
            self.write_predictions_file()

            if self.save_settings.plots:
                self.plot_optimizer_history(self.results.best_config_metric)

    def write_result_tree_to_file(self):
        try:
            local_file = os.path.join(self.save_settings.results_folder, 'photon_result_file.p')
            file_opened = open(local_file, 'wb')
            pickle.dump(self.results.to_son(), file_opened)
            file_opened.close()
        except OSError as e:
            Logger().error("Could not write results to local file")
            Logger().error(str(e))

    def write_predictions_file(self):
        if self.save_settings.save_predictions or self.save_settings.save_best_config_predictions:

            fold_nr_array = []
            y_pred_array = []
            y_true_array = []
            indices_array = []

            for outer_fold in self.results.outer_folds:
                score_info = outer_fold.best_config.inner_folds[0].validation
                y_pred_array = PHOTONDataHelper.stack_results(score_info.y_pred, y_pred_array)
                y_true_array = PHOTONDataHelper.stack_results(score_info.y_true, y_true_array)
                indices_array = PHOTONDataHelper.stack_results(score_info.indices, indices_array)
                fold_nr_array = PHOTONDataHelper.stack_results(np.ones((len(score_info.y_true),)) * outer_fold.fold_nr,
                                                               fold_nr_array)

            save_df = pd.DataFrame(data={'indices': indices_array, 'fold': fold_nr_array,
                                         'y_pred': y_pred_array, 'y_true': y_true_array})
            predictions_filename = os.path.join(self.save_settings.results_folder, 'outer_fold_predictions.csv')
            save_df.to_csv(predictions_filename)

    def write_summary(self):

        result_tree = self.results
        pp = pprint.PrettyPrinter(indent=4)

        text_list = []
        intro_text = """
PHOTON RESULT SUMMARY
-------------------------------------------------------------------

ANALYSIS NAME: {}
BEST CONFIG METRIC: {}
TIME OF RESULT: {}

        """.format(result_tree.name, result_tree.best_config_metric, result_tree.time_of_results)
        text_list.append(intro_text)

        if result_tree.dummy_estimator:
            dummy_text = """
-------------------------------------------------------------------
BASELINE - DUMMY ESTIMATOR
(always predict mean or most frequent target)

strategy: {}     

            """.format(result_tree.dummy_estimator.strategy)
            text_list.append(dummy_text)
            train_metrics = self.get_dict_from_metric_list(result_tree.dummy_estimator.test)
            text_list.append(self.print_table_for_performance_overview(train_metrics, "TEST"))
            train_metrics = self.get_dict_from_metric_list(result_tree.dummy_estimator.train)
            text_list.append(self.print_table_for_performance_overview(train_metrics, "TRAINING"))

        if result_tree.best_config:
            text_list.append("""

-------------------------------------------------------------------
OVERALL BEST CONFIG: 
{}            
            """.format(pp.pformat(result_tree.best_config.human_readable_config)))

        text_list.append("""
MEAN AND STD FOR ALL OUTER FOLD PERFORMANCES        
        """)

        train_metrics = self.get_dict_from_metric_list(result_tree.metrics_test)
        text_list.append(self.print_table_for_performance_overview(train_metrics, "TEST"))
        train_metrics = self.get_dict_from_metric_list(result_tree.metrics_train)
        text_list.append(self.print_table_for_performance_overview(train_metrics, "TRAINING"))

        for outer_fold in result_tree.outer_folds:
            text_list.append(self.print_outer_fold(outer_fold))

        final_text = ''.join(text_list)

        try:
            summary_filename = os.path.join(self.save_settings.results_folder, 'photon_summary.txt')
            text_file = open(summary_filename, "w")
            text_file.write(final_text)
            text_file.close()
            Logger().info("Saved results to summary file.")
        except OSError as e:
            Logger().error("Could not write summary file")
            Logger().error(str(e))

    def get_dict_from_metric_list(self, metric_list):
        best_config_metrics = {}
        for train_metric in metric_list:
            if not train_metric.metric_name in best_config_metrics:
                best_config_metrics[train_metric.metric_name] = {}
            operation_strip = train_metric.operation.split(".")[1]
            best_config_metrics[train_metric.metric_name][operation_strip] = np.round(train_metric.value, 6)
        return best_config_metrics

    def print_table_for_performance_overview(self, metric_dict, header):
        x = PrettyTable()
        x.field_names = ["Metric Name", "MEAN", "STD"]
        for element_key, element_dict in metric_dict.items():
            x.add_row([element_key, element_dict["MEAN"], element_dict["STD"]])

        text = """
{}:
{}
                """.format(header, str(x))

        return text

    def print_outer_fold(self, outer_fold):

        pp = pprint.PrettyPrinter(indent=4)
        outer_fold_text = []

        if outer_fold.best_config is not None:
            outer_fold_text.append("""
-------------------------------------------------------------------
OUTER FOLD {}
-------------------------------------------------------------------
Best Config:
{}

Number of samples training {}
Class distribution training {}
Number of samples test {}
Class distribution test {}

            """.format(outer_fold.fold_nr, pp.pformat(outer_fold.best_config.human_readable_config),
                       outer_fold.best_config.inner_folds[0].number_samples_training,
                       outer_fold.class_distribution_validation,
                       outer_fold.best_config.inner_folds[0].number_samples_validation,
                       outer_fold.class_distribution_test))

            if outer_fold.best_config.config_failed:
                outer_fold_text.append("""
Config Failed: {}            
    """.format(outer_fold.best_config.config_error))

            else:
                x = PrettyTable()
                x.field_names = ["Metric Name", "Train Value", "Test Value"]
                metrics_train = outer_fold.best_config.inner_folds[0].training.metrics
                metrics_test = outer_fold.best_config.inner_folds[0].validation.metrics

                for element_key, element_value in metrics_train.items():
                    x.add_row([element_key, np.round(element_value, 6), np.round(metrics_test[element_key], 6)])
                outer_fold_text.append("""
PERFORMANCE:
{}



                """.format(str(x)))

        return ''.join(outer_fold_text)
