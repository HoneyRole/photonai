import csv
import numpy as np


class LogExtractor:
    def __init__(self, result_tree):
        self.analysis_id = self.result_tree.name
        self.result_tree = result_tree

    def extract_csv(self, filename: str, with_timestamp: bool = True):
        start_time = 'not implemented!'
        # ToDo the duration "might" not the right one! ;)
        duration = self.result_tree.config_list[0].fit_duration
        outer_folds = self.result_tree.config_list[0].fold_list
        outer_folds_stat = self.get_outer_folds_stat(outer_folds)
        inner_hp_configuration_folds = self.get_folds_stat_for_hp_configs_for_outer_folds(outer_folds)
        stats = Stats(self.analysis_id, duration, start_time, outer_folds_stat, inner_hp_configuration_folds)
        stats.to_csv_file(filename, with_timestamp)

    def get_outer_folds_stat(self, outer_folds: list):
        outer_folds_stat = []
        for fold in outer_folds:
            outer_folds_stat.append(self.get_outer_fold_stat(fold))
        return FoldsStat(outer_folds_stat, "all outer folds")

    def get_outer_fold_stat(self, fold):
        config = fold.test.config_list[0].config_dict
        fold_metrics = self.get_fold_metrics_from_fold(fold)
        return FoldStat(config, fold.number_samples_test, fold.number_samples_train, fold_metrics)

    def get_fold_metrics_from_fold(self, fold):
        fold_metrics = []
        for metric_name in self.get_used_metric_names_form_fold(fold):
            fold_metrics.append(self.get_fold_metric_form_fold(metric_name, fold))
        return fold_metrics

    @staticmethod
    def get_used_metric_names_form_fold(fold):
        metrics = set()
        for metric in fold.train.config_list[0].fold_metrics_train:
            metrics.add(metric.metric_name)
        return list(metrics)

    @staticmethod
    def get_fold_metric_form_fold(metric_name, fold):
        train_value = fold.test.config_list[0].fold_list[0].train.metrics[metric_name]
        test_value = fold.test.config_list[0].fold_list[0].test.metrics[metric_name]
        return FoldMetric(metric_name, train_value, test_value)

    def get_folds_stat_for_hp_configs_for_outer_folds(self, outer_folds):
        folds_stat_for_hp_configs_for_outer_folds = []
        outer_fold_index = 0
        for outer_fold in outer_folds:
            hp_configs = outer_fold.train.config_list
            folds_stat_for_hp_configs_for_outer_folds += self.get_folds_stat_for_hp_configs(hp_configs,
                                                                                            outer_fold_index)
            outer_fold_index += 1
        return folds_stat_for_hp_configs_for_outer_folds

    def get_folds_stat_for_hp_configs(self, hp_configs: list, position_in_outer_cv_fold: int):
        hp_configs_folds_stat = []
        index = 0
        for hp_config in hp_configs:
            level_description = "Outer CV fold: {0}, Configuration: {1}".format(position_in_outer_cv_fold, index)
            hp_configs_folds_stat.append(self.get_folds_stat_for_hp_config(hp_config, level_description))
            index += 1
        return hp_configs_folds_stat

    def get_folds_stat_for_hp_config(self, hp_config, level_description: str):
        folds_stat_for_config = []
        config_parameter = hp_config.config_dict
        for fold in hp_config.fold_list:
            folds_stat_for_config.append(self.get_fold_stat_for_config(fold, config_parameter))
        return FoldsStat(folds_stat_for_config, level_description)

    def get_fold_stat_for_config(self, fold, config_parameter):
        fold_metrics = self.get_fold_metrics_from_inner_fold(fold)
        return FoldStat(config_parameter, fold.number_samples_test, fold.number_samples_train, fold_metrics)

    def get_fold_metrics_from_inner_fold(self, fold):
        fold_metrics = []
        for metric_name in self.get_used_metric_names_form_inner_fold(fold):
            fold_metrics.append(self.get_fold_metric_form_inner_fold(metric_name, fold))
        return fold_metrics

    @staticmethod
    def get_used_metric_names_form_inner_fold(fold):
        metric_names = set()
        for metric_key in fold.train.metrics:
            metric_names.add(metric_key)
        return list(metric_names)

    @staticmethod
    def get_fold_metric_form_inner_fold(metric_name, fold):
        train_value = fold.train.metrics[metric_name]
        test_value = fold.test.metrics[metric_name]
        return FoldMetric(metric_name, train_value, test_value)


class Stats:
    def __init__(self, name, duration, started_at, outer_folds_stat, inner_hp_configurations_folds_stat: list):
        self.name = name
        self.duration = duration
        self.started_at = started_at
        self.outer_folds_stat = outer_folds_stat
        self.inner_hp_configurations_folds_stat = inner_hp_configurations_folds_stat

    @staticmethod
    def description(self):
        out = """
        Analysis ID: {0}
        Duration:    {1}
        Started at:  {2}
        """.format(self.name, self.duration, self.started_at)
        out += self.outer_folds_stat.description()
        return out

    def to_csv_file(self, filename: str, with_timestamp: bool = True):
        if with_timestamp:
            import datetime
            import time
            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M')
            if filename.lower().endswith(".csv"):
                filename = "{0}_{1}.csv".format(filename[:-4], st)
            else:
                filename = "{0}_{1}.csv".format(filename, st)

        folds_array = self.get_description_array()
        folds_array_transpose = list(map(list, zip(*folds_array)))

        with open(filename, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            # Header
            csv_writer.writerow(["Analysis ID", self.name])
            csv_writer.writerow(["Duration", self.duration])
            csv_writer.writerow(["Started at", self.started_at])
            csv_writer.writerow([""])

            # Body with Stats
            for i in range(0, len(folds_array_transpose)):
                csv_writer.writerow(folds_array_transpose[i])

    def get_description_array(self):
        description_array = []
        headlines_outer = self.outer_folds_stat.get_description_array_headlines()
        headlines_inner = self.inner_hp_configurations_folds_stat[0].get_description_array_headlines()
        if len(headlines_outer) >= len(headlines_inner):
            description_array.append(headlines_outer)
            min_length = len(headlines_outer)
        else:
            description_array.append(headlines_inner)
            min_length = len(headlines_inner)
        description_array.append(self.outer_folds_stat.get_description_array_folds(min_length))
        for stat in self.inner_hp_configurations_folds_stat:
            description_array.append(stat.get_description_array_folds(min_length))
        return description_array


class FoldsStat:
    def __init__(self, folds_stat: list, level_description: str):
        self.folds_stat = folds_stat
        self.level_description = level_description

    def description(self):
        out = """
        Level: {0}
        """.format(self.level_description)
        for metric_name in self.get_used_metrics():
            out += ("""
            {0}:
              Test:
                Mean: {1}
                STD:  {2}
              Train:
                Mean: {3}
                STD:  {4}
            """.format(metric_name, self.get_mean_for_metric(metric_name)['mean_test'],
                       self.get_std_for_metric(metric_name)['std_test'],
                       self.get_mean_for_metric(metric_name)['mean_train'],
                       self.get_std_for_metric(metric_name)['std_train']))
        idx = 0
        for fold_stat in self.folds_stat:
            out += ("""
            
            Fold No. {0}
              Config:  {1}
              Number of test samples:  {2}
              Number of train samples: {3}""").format(idx, fold_stat.config, fold_stat.number_samples_test,
                                                      fold_stat.number_samples_train)
            for metric in fold_stat.fold_metrics:
                out += """
              {0}:
                Test:  {1}
                Train: {2} """.format(metric.name, metric.test_value, metric.train_value)
            idx += 1
        return out

    def get_description_array_headlines(self):
        # Level description
        description_array = ["Level description"]
        for _ in self.get_used_metrics():
            # Name Metric
            description_array.append("Name Metric")
            # Mean Test
            description_array.append("Mean Test")
            # Std Test
            description_array.append("STD Test")
            # Mean Train
            description_array.append("Mean Train")
            # Std Test
            description_array.append("STD Train")
            # Blank Line
            description_array.append("")
        idx = 0
        for fold_stat in self.folds_stat:
            # Fold Number
            description_array.append("Fold Number")
            # Fold Configuration
            description_array.append("Configuration")
            # Number of test samples
            description_array.append("Number of test samples")
            # Number of train samples
            description_array.append("Number of train samples")
            for _ in fold_stat.fold_metrics:
                # Name Metric
                description_array.append("Name Metric")
                # Test
                description_array.append("Test")
                # Train
                description_array.append("Train")
                # Blank Line
                description_array.append("")
            # Blank Line
            description_array.append("")
            idx += 1
        return description_array

    def get_description_array_folds(self, min_length: int = 0):
        # Level description
        description_array = [self.level_description]
        for metric_name in self.get_used_metrics():
            # Name Metric
            description_array.append(metric_name)
            # Mean Test
            description_array.append(str(self.get_mean_for_metric(metric_name)['mean_test']))
            # Std Test
            description_array.append(str(self.get_std_for_metric(metric_name)['std_test']))
            # Mean Train
            description_array.append(str(self.get_mean_for_metric(metric_name)['mean_train']))
            # Std Test
            description_array.append(str(self.get_std_for_metric(metric_name)['std_train']))
            # Blank Line
            description_array.append("")
        idx = 0
        for fold_stat in self.folds_stat:
            # Fold Number
            description_array.append(idx)
            # Fold Configuration
            description_array.append(fold_stat.config)
            # Number of test samples
            description_array.append(fold_stat.number_samples_test)
            # Number of train samples
            description_array.append(fold_stat.number_samples_train)
            for metric in fold_stat.fold_metrics:
                # Name Metric
                description_array.append(metric.name)
                # Test
                description_array.append(metric.test_value)
                # Train
                description_array.append(metric.train_value)
                # Blank Line
                description_array.append("")
            # Blank Line
            description_array.append("")
            idx += 1
        while len(description_array) < min_length:
            description_array.append("")
        return description_array

    def get_mean_for_metric(self, metric):
        train = []
        test = []
        for fold in self.folds_stat:
            for f_metric in fold.fold_metrics:
                if f_metric.name == metric:
                    train.append(f_metric.train_value)
                    test.append(f_metric.test_value)
        mean_train = np.mean(train)
        mean_test = np.mean(test)
        return {'mean_train': mean_train, 'mean_test': mean_test}

    def get_std_for_metric(self, metric):
        train = []
        test = []
        for fold in self.folds_stat:
            for f_metric in fold.fold_metrics:
                if f_metric.name == metric:
                    train.append(f_metric.train_value)
                    test.append(f_metric.test_value)
        std_train = np.std(train)
        std_test = np.std(test)
        return {'std_train': std_train, 'std_test': std_test}

    def get_used_metrics(self):
        metrics = []
        for f_metrics in self.folds_stat[0].fold_metrics:
            metrics.append(f_metrics.name)
        return metrics


class FoldStat:
    def __init__(self, config, number_samples_test: int, number_samples_train: int, fold_metrics: list):
        self.config = config
        self.number_samples_test = number_samples_test
        self.number_samples_train = number_samples_train
        self.fold_metrics = fold_metrics


class FoldMetric:
    def __init__(self, name: str, train_value, test_value):
        self.name = name
        self.train_value = train_value
        self.test_value = test_value
