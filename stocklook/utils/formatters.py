"""
MIT License

Copyright (c) 2017 Zeke Barge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from numpy import nan
from pandas import Timestamp
import xml.etree.cElementTree as ET


STRINGS_TO_DTYPE = {'str': str,
                    'Timestamp': Timestamp,
                    'DateTime': Timestamp,
                    'datetime': Timestamp,
                    'float': float,
                    'int': int,
                    'bool': bool
                    }
STRINGS_TO_DTYPE.update(
    {v: v for v in STRINGS_TO_DTYPE.values()})
DOLLAR_CONVERSION_MAP = {'M': 1000000,
                         'B': 1000000000,}
NULLS = ['NA', None, 'None', 'null']

STRINGS_TO_FALSE = ['no', 'false',
                    'null', '',
                    'none', 'na',
                    'nan', 'nat',
                    '0', '0.0',
                    nan, 'n/a']


def camel_case_to_under_score(x):
    """
    CamelCase --> camel_case
    :param x: (str)
        The CamelCase string to
        be converted to pep8.
    :return: (str)
        The formatted pep8 string.
        lower case
        upper case prefixed with underscore.
    """
    string = ''
    x = str(x)
    for i, v in enumerate(x):
        if i == 0 or v.islower():
            string += v
        else:
            string += '_'
            string += v

    return string.lower()


def camel_case_to_under_score_dict(_dict):
    """
    :param _dict: (dict)
        A dictionary with camel cased keys.

    :return: (dict)
        A dictionary with pep8 cased keys.
        see stocklook.utils.formatters.camel_case_to_under_score
    """
    return {camel_case_to_under_score((k)): v
            for k, v in _dict.items()}


def format_dollar_letter_conversions(value):
    """
    Converts a string to float even if it contains illegal characters.

    Conversions:
    ------------

        '100M' --> 1000000000.00: 100 million
        '1B' --> 1000000000.00: 1 billion
        '$5.99' --> 5.99
        '4' --> 4.0
        '4.0' --> 4.0
        4.0 --> 4.0
        4 --> 4.0

    Note: Only the above conversions happen. strings suffixed
    with other characters will be removed and the float value
    will be returned.

    :param value: (str, int, float)
        The value to convert

    :return: (float)
        The float result.
        0 if it cannot be converted.
    """
    try:
        value = str(value).strip()
        first = value[0]
        last = value[-1].upper()

        # Trim $ or anything non numeric off front
        if not first.isnumeric():
            value = value.replace(first, '').strip()

        if not last.isdigit():
            value = value.replace(last, '').strip()
            try:
                value = float(value) * DOLLAR_CONVERSION_MAP[last]
            except KeyError:
                pass
        return float(value)
    except ValueError:
        return float(0)


def raw_string(x):
    try:
        return r"{}".format(x.__name__)
    except:
        return r"{}".format(x)


def ensure_float(x):
    # Returns a float or 0
    x = format_dollar_letter_conversions(
        str(x).replace('%', '').lstrip().rstrip())
    try:
        return float(x)
    except:
        return float(0)


def ensure_int(x):
    # Returns an int or 0
    x = format_dollar_letter_conversions(str(x)
                                         .replace('%', '')
                                         .replace('$', '')
                                         .lstrip()
                                         .rstrip())
    try:
        return int(x)
    except:
        return 0


def ensure_string(x):
    # Returns a string
    if x:
        try:
            return str(x)
        except:
            return ''
    return ''


def ensure_bool(x):
    """
    Returns True or False
    Uses stocklook.utils.formatters.STRINGS_TO_FALSE
    list to look up the value and determine False should be returned.
    :param x: (str, any)
        The value to evaluate for True or False.

    :return: (bool)
        False if possible else True.
    """

    x = str(x).lower().lstrip().rstrip()
    if x in STRINGS_TO_FALSE:
        return False
    return True


DEFAULT_TIMESTAMP = Timestamp('1900-01-01')


def ensure_datetime(x):
    """
    :param x: (str, datetime)
        A value to evaluate for datetime.

    :return: (pandas.Timestamp)
        A Timestamp object.
        If it can't be converted
        Timestamp('1900-01-01') is returned.
    """
    try:
        t = Timestamp(x)
        if 'NaT' in str(t):
            return DEFAULT_TIMESTAMP
        return t
    except:
        return DEFAULT_TIMESTAMP


DTYPE_CONVERTERS = {str: ensure_string,
                    float: ensure_float,
                    int: ensure_int,
                    bool: ensure_bool,
                    Timestamp: ensure_datetime}


NAME = 'NAME'
RENAME = 'RENAME'
DTYPE = 'DTYPE'
FIELDS = 'FIELDS'
INCLUDE = 'INCLUDE'


class DictParser:
    def __init__(self):
        pass

    @staticmethod
    def parse_dtypes(record_dict, dtype_map, default=str, raise_on_error=True):
        """
        parses the dtypes of the values in record_dict
        using the functions defined in the field_dtypes_dict
        record_dict            A dictionary of {field_name:value}
        dtype_map              A dictionary of {field_name:dtype}
        default                The datatype to default to.
        raise_on_error         True raises KeyErrors, False defaults to default dtype.
        """
        new = {}
        for field, value in record_dict.items():
            try:
                dtype = dtype_map[field]
            except KeyError:
                if raise_on_error:
                    raise
                dtype = str

            try:
                new[field] = DTYPE_CONVERTERS[dtype](value)
            except KeyError:
                if raise_on_error:
                    raise NotImplementedError("dtype '{}' is unsupported".format(dtype))
                new[field] = default(value)

        return new

    @staticmethod
    def rename_dict(dict_to_rename, dict_map):
        new = {}
        for field, value in dict_to_rename.items():
            try:
                field = dict_map[field]
            except KeyError:
                pass
            new[field] = value
        return new

    @staticmethod
    def get_merged_dict(*dicts):
        merged_dict = {}
        [merged_dict.update(d) for d in dicts]
        return merged_dict

    @staticmethod
    def get_dict_keys(dict_to_filter, include_list):
        return {field: value for field, value in dict_to_filter.items()
                if field in include_list}

    @staticmethod
    def drop_dict_keys(dict_to_filter, exclude_list):
        return {field: value for field, value in dict_to_filter.items()
                if not field in exclude_list}

    @staticmethod
    def drop_dict_values(dict_to_filter, exclude_list):
        return {field: value for field, value in dict_to_filter.items()
                if not value in exclude_list}


class XmlList(list):
    def __init__(self, aList):
        for element in aList:
            if element:
                # treat like dict
                if len(element) == 1 or element[0].tag != element[1].tag:
                    self.append(XmlDict(element))
                # treat like list
                elif element[0].tag == element[1].tag:
                    self.append(XmlList(element))
            elif element.text:
                text = element.text.strip()
                if text:
                    self.append(text)


class XmlDict(dict):
    '''
    Example usage:

    >>> tree = ElementTree.parse('your_file.xml')
    >>> root = tree.getroot()
    >>> xmldict = XmlDictConfig(root)

    Or, if you want to use an XML string:

    >>> root = ElementTree.XML(xml_string)
    >>> xmldict = XmlDictConfig(root)

    And then use xmldict for what it is... a dict.
    '''

    def __init__(self, parent_element):
        if isinstance(parent_element, (str, bytes)):
            parent_element = ET.XML(parent_element)
        if parent_element.items():
            self.update(dict(parent_element.items()))
        for element in parent_element:
            if element:
                # treat like dict - we assume that if the first two tags
                # in a series are different, then they are all different.
                if len(element) == 1 or element[0].tag != element[1].tag:
                    aDict = XmlDict(element)
                # treat like list - we assume that if the first two tags
                # in a series are the same, then the rest are the same.
                else:
                    # here, we put the list in dictionary; the key is the
                    # tag name the list elements all share in common, and
                    # the value is the list itself
                    aDict = {element[0].tag: XmlList(element)}
                # if the tag has attributes, add those to the dict
                if element.items():
                    aDict.update(dict(element.items()))
                self.update({element.tag: aDict})
            # this assumes that if you've got an attribute in a tag,
            # you won't be having any text. This may or may not be a
            # good idea -- time will tell. It works for the way we are
            # currently doing XML configuration files...
            elif element.items():
                self.update({element.tag: dict(element.items())})
            # finally, if there are no child tags and no attributes, extract
            # the text
            else:
                self.update({element.tag: element.text})


def _test_XmlDict():
    string = b'<?xml version="1.0" encoding="UTF-8" ?>\n<response uri="/crm/private/xml/CustomModule4/insertRecords">' \
             b'<result><message>Record(s) added successfully</message><recorddetail><FL val="Id">1706004000002464015</FL>' \
             b'<FL val="Created Time">2016-09-26 16:15:32</FL><FL val="Modified Time">2016-09-26 16:15:32</FL><FL val="Created By">' \
             b'<![CDATA[Data]]></FL><FL val="Modified By"><![CDATA[Data]]></FL></recorddetail></result></response>\n'
    xd = XmlDict(string)
    assert isinstance(xd, dict), "Expected to get a dictionary, not {}".format(type(xd))
    assert xd.get('uri', None) == '/crm/private/xml/CustomModule4/insertRecords'
    details = xd['result']['recorddetail']
    assert isinstance(details, dict), "Expected to get a dictionary, not {}".format(type(details))
    print('tests passed OK')


def sanatize_field(field):
    for char in ['-', ' ', '___', '__']:
        field = field.replace(char, '_')
    return ''.join(x for x in str(field) if x.isalnum() or x == '_').lower()
