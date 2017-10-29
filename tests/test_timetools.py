from stocklook.utils.timetools import *
import pytest

SAMPLE_TIMES = ['2017-08-10', 1479076800, 1479076800.0,
                '1479076800', '2000-10-01 10:15:25',

                '9/15/2010', '1479076800.05']


@pytest.mark.parametrize('dt', SAMPLE_TIMES)
def test_utc_serialization(dt):
    """
    Ensures that serialization and deserialization
    of datetime objects and integers always returns the expected value - even if the expected
    value is what's given. and that time zone converzions do not change the original value.
    :param dt:
    :return:
    """
    dt_ser = timestamp_to_local(dt)
    dt_unser = timestamp_to_utc_int(dt_ser)
    dt_unser2 = timestamp_to_utc_int(dt)

    dt_unser = int(dt_unser)
    dt_unser2 = int(dt_unser2)
    assert dt_unser == dt_unser2, "{}".format(dt_unser - dt_unser2)

    dt3 = timestamp_to_local(dt_unser)
    dt4 = timestamp_to_local(dt_unser2)
    for i in range(1, 10):
        check_dt1 = dt3 + timedelta(days=i)
        check_dt2 = dt4 + timedelta(days=i)
        assert check_dt1 == check_dt2
        check_u1 = timestamp_to_utc_int(check_dt1)
        check_u2 = timestamp_to_utc_int(check_dt2)
        assert check_u1 == check_u2


def test_time_tuples():
    dt = 1479076800
    dt1 = datetime.utcfromtimestamp(dt)
    print(dt)
    dt2 = timegm(dt1.utctimetuple())
    dt3 = timestamp_to_local(dt)
    dt4 = timegm(dt3.utctimetuple())
    assert dt == dt2
    assert dt == dt4