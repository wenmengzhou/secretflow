import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder as SkLabelEncoder
from sklearn.preprocessing import OneHotEncoder as SkOneHotEncoder
from sklearn.utils.validation import column_or_1d

from secretflow.data.base import Partition, reveal
from secretflow.data.horizontal import read_csv as h_read_csv
from secretflow.data.horizontal.dataframe import HDataFrame
from secretflow.data.mix.dataframe import MixDataFrame
from secretflow.data.vertical.dataframe import VDataFrame
from secretflow.preprocessing.encoder import LabelEncoder, OneHotEncoder
from secretflow.security.aggregation.device_aggregator import \
    DeviceAggregator
from secretflow.security.compare.plain_comparator import \
    PlainComparator
from tests.basecase import DeviceTestCase


class TestLabelEncoder(DeviceTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        path_alice = 'tests/datasets/iris/horizontal/iris.alice.csv'
        path_bob = 'tests/datasets/iris/horizontal/iris.bob.csv'
        cls.hdf_alice = pd.read_csv(path_alice)
        cls.hdf_bob = pd.read_csv(path_bob)
        cls.hdf = h_read_csv(
            {cls.alice: path_alice, cls.bob: path_bob},
            aggregator=DeviceAggregator(cls.carol),
            comparator=PlainComparator(cls.carol))

        vdf_alice = pd.DataFrame({'a1': ['K5', 'K1', None, 'K6'],
                                  'a2': ['A5', 'A1', 'A2', 'A6'],
                                  'a3': [5, 1, 2, 6]})

        vdf_bob = pd.DataFrame({'b4': [10.2, 20.5, None, -0.4],
                                'b5': ['B3', None, 'B9', 'B4'],
                                'b6': [3, 1, 9, 4]})

        cls.vdf_alice = vdf_alice
        cls.vdf_bob = vdf_bob
        cls.vdf = VDataFrame(
            {cls.alice: Partition(data=cls.alice(lambda: vdf_alice)()),
             cls.bob: Partition(data=cls.bob(lambda: vdf_bob)())})

    def test_on_hdataframe_should_ok(self):
        # GIVEN
        encoder = LabelEncoder()

        # WHEN
        value = encoder.fit_transform(self.hdf['class'])

        # THEN
        sk_encoder = SkLabelEncoder()
        sk_encoder.fit(column_or_1d(pd.concat([self.hdf_alice[['class']], self.hdf_bob[['class']]])))
        expect_alice = sk_encoder.transform(column_or_1d(self.hdf_alice[['class']]))[np.newaxis].T
        np.testing.assert_equal(reveal(value.partitions[self.alice].data), expect_alice)
        expect_bob = sk_encoder.transform(column_or_1d(self.hdf_bob[['class']]))[np.newaxis].T
        np.testing.assert_equal(reveal(value.partitions[self.bob].data), expect_bob)

    def test_on_vdataframe_should_ok(self):
        # GIVEN
        encoder = LabelEncoder()

        # WHEN
        value = encoder.fit_transform(self.vdf['a2'])

        # THEN
        self.assertEqual(len(value.partitions), 1)
        sk_encoder = SkLabelEncoder()
        expect_alice = sk_encoder.fit_transform(column_or_1d(self.vdf_alice[['a2']]))[np.newaxis].T
        np.testing.assert_equal(reveal(value.partitions[self.alice].data), expect_alice)

    def test_on_h_mixdataframe_should_ok(self):
        # GIVEN
        df = pd.DataFrame({'a1': ['A1', 'B1', None, 'D1', None, 'B4', 'C4', 'D4']})
        h_part0 = VDataFrame(
            {self.alice: Partition(data=self.alice(lambda: df.iloc[:4, :])())})
        h_part1 = VDataFrame(
            {self.alice: Partition(data=self.alice(lambda: df.iloc[4:, :])())})
        h_mix = MixDataFrame(partitions=[h_part0, h_part1])

        encoder = LabelEncoder()

        # WHEN
        value = encoder.fit_transform(h_mix)

        # THEN
        sk_encoder = SkLabelEncoder()
        expected = sk_encoder.fit_transform(column_or_1d(df))[np.newaxis].T
        np.testing.assert_equal(
            pd.concat(
                [reveal(value.partitions[0].partitions[self.alice].data),
                 reveal(value.partitions[1].partitions[self.alice].data)]),
            expected)

    def test_on_v_mixdataframe_should_ok(self):
        # GIVEN
        df = pd.DataFrame({'a1': ['A1', 'B1', None, 'D1', None, 'B4', 'C4', 'D4']})
        v_part0 = HDataFrame(
            {self.alice: Partition(data=self.alice(lambda: df.iloc[:4, :])()),
             self.bob: Partition(data=self.bob(lambda: df.iloc[4:, :])())},
            aggregator=DeviceAggregator(self.carol), comparator=PlainComparator(self.carol))
        v_mix = MixDataFrame(partitions=[v_part0])

        encoder = LabelEncoder()

        # WHEN
        value = encoder.fit_transform(v_mix)

        # THEN
        sk_encoder = SkLabelEncoder()
        expected = sk_encoder.fit_transform(column_or_1d(df))[np.newaxis].T
        np.testing.assert_equal(
            pd.concat(
                [reveal(value.partitions[0].partitions[self.alice].data),
                 reveal(value.partitions[0].partitions[self.bob].data)]),
            expected)

    def test_on_hdataframe_more_than_one_column_should_error(self):
        with self.assertRaisesRegex(AssertionError, 'DataFrame to encode should have one and only one column'):
            encoder = LabelEncoder()
            encoder.fit_transform(self.hdf)

    def test_on_vdataframe_more_than_one_column_should_error(self):
        with self.assertRaisesRegex(AssertionError, 'DataFrame to encode should have one and only one column'):
            encoder = LabelEncoder()
            encoder.fit_transform(self.vdf)

    def test_should_error_when_not_dataframe(self):
        encoder = LabelEncoder()
        with self.assertRaisesRegex(AssertionError, 'Accepts HDataFrame/VDataFrame/MixDataFrame only'):
            encoder.fit(['test'])
        encoder.fit(self.vdf['a2'])
        with self.assertRaisesRegex(AssertionError, 'Accepts HDataFrame/VDataFrame/MixDataFrame only'):
            encoder.transform(['test'])

    def test_transform_should_error_when_not_fit(self):
        with self.assertRaisesRegex(AssertionError, 'Encoder has not been fit yet.'):
            LabelEncoder().transform('test')


class TestOneHotEncoder(DeviceTestCase):
    def setUp(self) -> None:
        super().setUp()
        path_alice = 'tests/datasets/iris/horizontal/iris.alice.csv'
        path_bob = 'tests/datasets/iris/horizontal/iris.bob.csv'
        self.hdf_alice = pd.read_csv(path_alice)
        self.hdf_bob = pd.read_csv(path_bob)
        self.hdf = h_read_csv(
            {self.alice: path_alice, self.bob: path_bob},
            aggregator=DeviceAggregator(self.carol),
            comparator=PlainComparator(self.carol))

        vdf_alice = pd.DataFrame({'a1': ['K5', 'K1', None, 'K6'],
                                  'a2': ['A5', 'A1', 'A2', 'A6'],
                                  'a3': [5, 1, 2, 1]})

        vdf_bob = pd.DataFrame({'b4': [10.2, 20.5, None, -0.4],
                                'b5': ['B3', None, 'B3', 'B4'],
                                'b6': [3, 1, 9, 4]})

        self.vdf_alice = vdf_alice
        self.vdf_bob = vdf_bob
        self.vdf = VDataFrame(
            {self.alice: Partition(data=self.alice(lambda: vdf_alice)()),
             self.bob: Partition(data=self.bob(lambda: vdf_bob)())})

    def test_on_hdataframe_should_ok(self):
        # GIVEN
        encoder = OneHotEncoder()

        # WHEN
        value = encoder.fit_transform(self.hdf['class'])

        # THEN
        sk_encoder = SkOneHotEncoder()
        sk_encoder.fit(pd.concat([self.hdf_alice[['class']], self.hdf_bob[['class']]]))
        expect_alice = sk_encoder.transform(self.hdf_alice[['class']]).toarray()
        np.testing.assert_equal(reveal(value.partitions[self.alice].data), expect_alice)
        expect_bob = sk_encoder.transform(self.hdf_bob[['class']]).toarray()
        np.testing.assert_equal(reveal(value.partitions[self.bob].data), expect_bob)

    def test_on_vdataframe_should_ok(self):
        # GIVEN
        encoder = OneHotEncoder()

        # WHEN
        value = encoder.fit_transform(self.vdf[['a1', 'a2', 'b5']])

        # THEN
        sk_encoder = SkOneHotEncoder()
        expect_alice = sk_encoder.fit_transform(self.vdf_alice[['a1', 'a2']]).toarray()
        np.testing.assert_equal(reveal(value.partitions[self.alice].data), expect_alice)
        expect_bob = sk_encoder.fit_transform(self.vdf_bob[['b5']]).toarray()
        np.testing.assert_equal(reveal(value.partitions[self.bob].data), expect_bob)

    def test_on_h_mixdataframe_should_ok(self):
        # GIVEN
        df_part0 = pd.DataFrame({'a1': ['A1', 'B1', None, 'D1', None, 'B4', 'C4', 'C4'],
                                 'a2': [5, 5, 2, 6, 15, None, 23, 6]})

        df_part1 = pd.DataFrame({'b4': [10.2, 20.5, None, -0.4, None, 0.5, None, -10.4]})
        h_part0 = VDataFrame(
            {self.alice: Partition(data=self.alice(lambda: df_part0.iloc[:4, :])()),
             self.bob: Partition(data=self.bob(lambda: df_part1.iloc[:4, :])())})
        h_part1 = VDataFrame(
            {self.alice: Partition(data=self.alice(lambda: df_part0.iloc[4:, :])()),
             self.bob: Partition(data=self.bob(lambda: df_part1.iloc[4:, :])())})
        h_mix = MixDataFrame(partitions=[h_part0, h_part1])

        encoder = OneHotEncoder()

        # WHEN
        value = encoder.fit_transform(h_mix)

        # THEN
        sk_encoder = SkOneHotEncoder()
        expected = sk_encoder.fit_transform(pd.concat([df_part0, df_part1], axis=1)).toarray()
        np.testing.assert_equal(
            pd.concat([
                pd.concat(
                    [reveal(value.partitions[0].partitions[self.alice].data),
                     reveal(value.partitions[1].partitions[self.alice].data)]),
                pd.concat(
                    [reveal(value.partitions[0].partitions[self.bob].data),
                     reveal(value.partitions[1].partitions[self.bob].data)])], axis=1),
            expected)

    def test_on_v_mixdataframe_should_ok(self):
        # GIVEN
        df_part0 = pd.DataFrame({'a1': ['A1', 'B1', None, 'D1', None, 'B4', 'C4', 'C4'],
                                 'a2': [5, 5, 2, 6, 15, None, 23, 6]})

        df_part1 = pd.DataFrame({'b4': [10.2, 20.5, None, -0.4, None, 0.5, None, -10.4]})
        v_part0 = HDataFrame(
            {self.alice: Partition(data=self.alice(lambda: df_part0.iloc[:4, :])()),
             self.bob: Partition(data=self.bob(lambda: df_part0.iloc[4:, :])())},
            aggregator=DeviceAggregator(self.carol), comparator=PlainComparator(self.carol))
        v_part1 = HDataFrame(
            {self.alice: Partition(data=self.alice(lambda: df_part1.iloc[:4, :])()),
             self.bob: Partition(data=self.bob(lambda: df_part1.iloc[4:, :])())},
            aggregator=DeviceAggregator(self.carol), comparator=PlainComparator(self.carol))
        v_mix = MixDataFrame(partitions=[v_part0, v_part1])

        encoder = OneHotEncoder()

        # WHEN
        value = encoder.fit_transform(v_mix)

        # THEN
        sk_encoder = SkOneHotEncoder()
        expected = sk_encoder.fit_transform(pd.concat([df_part0, df_part1], axis=1)).toarray()
        np.testing.assert_equal(
            pd.concat([
                pd.concat(
                    [reveal(value.partitions[0].partitions[self.alice].data),
                     reveal(value.partitions[0].partitions[self.bob].data)]),
                pd.concat(
                    [reveal(value.partitions[1].partitions[self.alice].data),
                     reveal(value.partitions[1].partitions[self.bob].data)])], axis=1),
            expected)

    def test_should_error_when_not_dataframe(self):
        encoder = OneHotEncoder()
        with self.assertRaisesRegex(AssertionError, 'Accepts HDataFrame/VDataFrame/MixDataFrame only'):
            encoder.fit(['test'])
        encoder.fit(self.hdf)
        with self.assertRaisesRegex(AssertionError, 'Accepts HDataFrame/VDataFrame/MixDataFrame only'):
            encoder.transform(['test'])

    def test_transform_should_error_when_not_fit(self):
        with self.assertRaisesRegex(AssertionError, 'Encoder has not been fit yet.'):
            OneHotEncoder().transform('test')
