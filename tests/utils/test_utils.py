import os
import pytest

from src.utils.utils import eval_bool, print_banner, get_properties


def test_print_banner():
    p = print_banner()
    assert p is None


def test_eval_bool_true():
    ret = eval_bool("yes")
    assert ret == True


def test_eval_bool_true_numerical():
    ret = eval_bool("1")
    assert ret == True


def test_eval_bool_false():
    ret = eval_bool("No")
    assert ret == False


def test_eval_bool_false_numerical():
    ret = eval_bool("0")
    assert ret == False


def test_eval_bool_attribute_error():
    with pytest.raises(AttributeError):
        eval_bool(9)


def test_get_properties_invalid_path():
    with pytest.raises(FileNotFoundError):
        get_properties("invalid.path")


def test_get_properties_valid_path():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    prop = get_properties(os.path.join(dir_path, "../../application.properties"))
    assert len(prop) > 0
