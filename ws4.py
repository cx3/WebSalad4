#!/usr/bin/Python37
from __future__ import annotations
from _io import _IOBase as ReadableFile
from lxml import html
from typing import Tuple, List, Any, Callable
from copy import deepcopy
from requests import get
from bs4 import BeautifulSoup as Soup
from bs4.element import Tag as BsTag
from bs4.element import NavigableString as Ns
import re


def is_url(s: str, relaxed_rules=True) -> bool:
    """
    Tells if param s is correct url
    :param s: url string to be tested
    :param relaxed_rules: if set to False, url starting with www without http:// like prefix are treated as incorrect
    :return: bool
    """
    if type(s) is str:
        regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if relaxed_rules:
            if '://' not in s:
                s = 'http://' + s
        return re.match(regex, s) is not None
    return False


def is_valid_html_tag(s: str) -> bool:
    """
    Tries to tell if :param s: as Python's str is valid str code (XML/HTML)
    :param s: Python's str
    :return: bool
    """

    s = s.replace('\n', '')
    s = s.lstrip() + s.rstrip()

    if s.startswith('<') and s.endswith('>'):
        if not bool(Soup(s.replace("'", '"'), 'html.parser').find()):
            return False
    return False


def partial_in(what: str, where: List[str] or Tuple[str]) -> bool:
    """
    Tells if string value in 'what' parameter is in any element of list. Each list element is set to str before
    comparision
    :param what: element to be checked
    :param where: list of any elements
    :return: bool
    """
    for x in where:
        if what in str(x):
            return True
    return False


def common_items(one: List[str] or Tuple[str], two: List[str] or Tuple[str], certain_match=True) -> List[str]:
    result = []
    if certain_match:
        for item in one:
            for _ in two:
                if item == _:
                    result.append(_)
    else:
        for item in one:
            for _ in two:
                if item in _ or _ in item:
                    result.append(_)
    return result


def str_remove(s: str, to_del: str = ('<html><body>', '</body></html>')) -> str:
    for what in to_del:
        s = s.replace(what, '')
    return s


def query_dict(d: dict) -> dict:
    if 'attrs' not in d:
        if 'tag_name' not in d:
            return {
                'tag_name': '',
                'attrs': d
            }
        else:
            return {
                'tag_name': d['tag_name'],
                'attrs': {k: v for k, v in d.items() if 'tag_name' != k}
            }
    else:
        result = {
            'tag_name': d.get('tag_name', ''),
            'attrs': d.get('attrs', {})
        }
    return result


class WebTag:

    def __init__(self, bs_tag: BsTag or str):
        """
        Objects of this class represents tags in XML/HTML code. WebSalad instances uses it to parse or iterate over the
        :param bs_tag: bs4.Tag instance or str with valid XML/HTML code
        """
        self.bs_tag = None
        if not isinstance(bs_tag, BsTag):
            bs_tag = str(bs_tag)
            if not is_valid_html_tag(bs_tag):
                raise TypeError
            bs_tag = Soup(bs_tag, 'html.parser').find_all()[0]
        self.bs_tag = bs_tag

    def keys(self) -> List[str]:
        """
        Returns list of str with keys of XML/HTML tag
        :return: list of str
        """
        return list(self.bs_tag.attrs.keys())

    def has_key(self, key) -> bool:
        """
        Tells if XML/HTML tag has key. Use asterisk at the end of key name to compare key names by partial name of it
        :return: bool
        """
        if key[-1] == '*':
            return partial_in(key[:-1], self.keys())
        return partial_in(key, self.keys())

    def has_key_value(self, key='', value='') -> bool:
        """
        Tells if XML/HTML tag has pair key to value. Both key and value may be partial
        :param key: tag key
        :param value: tag value binded with key
        :return: bool
        """
        v = self.__getitem__(key)
        if v:
            if isinstance(v, (list, tuple)):
                v = ' '.join(v)
            return value in v
        return False

    def has_all_keys_values(self, *dict_list, **pairs) -> bool:
        """
        Tells if XML/HTML tag has all pairs key-value, where all key-value pairs in pairs dict can be partial.
        You can mix one_dict variable list of dicts with variable arguments in :param pairs:, function will
        create one dictionary with pairs.
        :param dict_list: variable list of dicts. Passing other type than dict will raise TypeError
        :param pairs: dict with pairs to compare
        :return: bool
        """

        if not isinstance(dict_list, (list, tuple)):
            dict_list = [dict_list, ]
        for item in dict_list:
            if isinstance(item, dict):
                pairs.update(item)
            else:
                raise TypeError

        must_len = len(list(pairs.items()))
        count = 0
        for key, value in pairs.items():
            if self.has_key_value(key, value):
                count += 1
        return count == must_len

    def values(self) -> List[str]:
        """
        Tells values under keys of XML/HTML tag
        :return: list of str
        """
        vals = list(self.bs_tag.attrs.values())
        for index, v in enumerate(vals):
            if isinstance(v, (list, tuple)):
                vals[index] = ' '.join(v)
        return vals

    def items(self) -> List:
        """
        Returns list of tuples where each tuple consists of pair (key, value)
        :return:
        """
        return list(self.bs_tag.attrs.items())

    def find_all(self, tag_name='', **attrs) -> List[WebTag]:
        """
        Finds all children XML/HTML tags where tag_name matches and where all pairs key-value matches by partial compare
        :param tag_name: XML/HTML tag's name
        :param attrs: dictionary with key-value to partial compare
        :return: list of WebTag
        """
        tag_matching = Soup(self.__str__(), 'html.parser').find_all()
        result = []
        for wt in tag_matching:
            wt = WebTag(wt)
            if tag_name not in wt.name:
                continue
            match = True
            for key, value in attrs.items():
                if not wt.has_key_value(key, value):
                    match = False
            if match:
                result.append(wt)
        return result

    def find_by_xpath(self, xpath: str) -> List[WebTag]:
        """
        Allows to use XPath expression, enhancement, BeautifulSoup has not this functionality by itself ;-)
        :param xpath: str Xpath expression (see for more https://www.w3schools.com/xml/xml_xpath.asp)
        :return: list of WebTag
        """

        soup = Soup(self.__str__(), 'html.parser')
        result = []
        for next_match in html.fromstring(str(soup)).xpath(xpath):
            result.extend(soup.find_all(name=next_match.tag, attrs={k: v for k, v in next_match.attrib.items()}))

        return list(WebTag(_) for _ in result if isinstance(_, BsTag))

    def prettify(self, encoding=None, formatter="minimal"):
        """
        Returns styled HTML code
        :param encoding: check bs4 documentation
        :param formatter: check bs4 documentation
        :return: str with formatted code
        """

        return Soup(self.__str__(), 'html.parser').prettify(encoding, formatter)

    def __contains__(self, item: str or dict or WebTag) -> bool:
        """
        Tells if XML/HTML tag represented by this instance of WebTag contains :param item: of type
        * str:  WebTag is turned to str, then Pythons checks if item in str
        * dict: all children are checked if one of them has similar attributes to passed in item dict
        * WebTag: instance of WebTag is turned to dict for comparision
        :param item: str/dict/WebTag
        :return: bool
        """

        if isinstance(item, str):
            return item in str(self)
        if isinstance(item, WebTag):
            item = {
                'tag_name': item.name,
                'attrs': item.attrs
            }
        if isinstance(item, dict):
            item = query_dict(item)
            for child in self.bs_tag.children:
                if isinstance(child, BsTag):
                    if item['tag_name'] in child.name:
                        if WebTag(child).has_all_keys_values(**item['attrs']):
                            return True
        return False

    def __getitem__(self, item):
        """
        Allows to get value of key passed by partial content
        :param item: partial name of key
        :return: value binded to first key match
        """

        for key in self.bs_tag.attrs.keys():
            if item in key:
                return self.bs_tag.attrs[key]
        return False

    def __setitem__(self, key, value):
        """
        Allows to set value under key passed by partial name. If key was not found, value binded to partial key name is
        set to new key!
        :param key: partial or full key name
        :param value: value to be set
        :return: key name under which value was set
        """

        if isinstance(value, str):
            if ' ' in value:
                value = value.split(' ')
        for attr_key in self.bs_tag.attrs.keys():
            if attr_key == key in key:
                self.bs_tag.attrs[key] = value
                return key

    def __getattr__(self, item) -> Any:
        """
        Allows get attribute of WebTag or bs4.Tag instance dependently to where attribute was found
        :param item: attribute name in str (field, method)
        :return: attribute in Python's meaning (field, method)
        """

        if item not in dir(self):
            return getattr(self.bs_tag, item)
        return getattr(self, item)

    def __hash__(self):
        """
        Allows making instance of WebTag as key in dictionary
        :return: hash
        """
        return hash(self.__str__())

    def __str__(self):
        """
        Turn this instance to Python's str
        :return: str
        """
        return str(self.bs_tag)

    def __repr__(self):
        """
        See for more: https://www.geeksforgeeks.org/str-vs-repr-in-python/
        """
        str_value = self.__str__().replace('\n', '')
        if WebTag.full_repr:
            return f"WebTag({str_value})"
        return str_value

    full_repr = False


class WebSalad(object):

    def __init__(self,
                 code: str or Soup or bytes or bytearray or List[Soup] or List[WebTag] or List[WebSalad],
                 **kwargs):
        """
        bs4.BeautifulSoup extension. Allows in flexible and convenient way iterate, find, cut data from nested XML/HTML
        structure. Some kind of wrapper over bs4.BeautifulSoup.  Allows knowing partial key names and/or values of tags
        to iterate over nested XML/HTML structure of scraped pages.
        :param code:
            Dev can pass HTML source code as str, URL string, bs4.BeautifulSoup object, pointer to Python built-in file
            If passed hyperlink, requests module scraps data from web. If passed list of something, all elements are to
            be converted to str, then merged into one str that is passed to bs4.BeautifulSoup object
        :param kwargs:
            :key parser: parser used by internal bs4.BeautifulSoup object, by default it is 'html.parser'
            :key no_headers: tells bs4.BeautifulSoup not to use headers while connecting to remote server
            :key headers: pass dictionary to be sent to remote server if you do not want default headers
            :key iter_type: use one of WebSalad, BeautifulSoup, BsTag, WebTag

        """
        x = code
        tx = type(x)
        parser = kwargs.get('parser', 'html.parser')
        if tx is list or tx is tuple:
            x = ''.join([str(_) for _ in x])
            tx = str

        if tx is str:
            if is_url(x):

                def safe_get(link, headers_=None, parser_='lxml'):
                    starts_ok = False
                    for _ in ['://', 'http://', 'https://']:
                        if link.startswith(_):
                            starts_ok = True
                    if not starts_ok:
                        link = 'http://' + link
                    if headers_:
                        data = get(link, headers=headers_).content
                    else:
                        data = get(link).content
                    return Soup(data, parser=parser_)

                if kwargs.get('no_headers', False):
                    self.soup: Soup = safe_get(x)  # Soup(get(x).content, parser)
                elif kwargs.get('default_headers', True):
                    default_headers = {
                        'User-Agent':
                            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                            'Chrome/56.0.2924.76 Safari/537.36',
                    }
                    self.soup: Soup = safe_get(x, default_headers, parser)
                    # Soup(get(x, headers=default_headers).content, parser)
                elif 'headers' in kwargs:
                    self.soup: Soup = safe_get(x, kwargs['headers'], parser)
            else:
                self.soup: Soup = Soup(x, parser)
        elif tx is Soup:
            self.soup: Soup = x
        elif issubclass(x.__class__, ReadableFile):
            self.soup: Soup = Soup(x.read(), parser)
        elif tx is WebSalad:
            self.soup = deepcopy(x.soup)
        elif tx is bytes or tx is bytearray:
            self.soup: Soup = Soup(x, parser)

        if not hasattr(self, 'soup'):
            raise AttributeError(
                f'arg`s type must be one of str/Soup/bytes/bytearray/file. current type provided: {type(x)}')

        kwargs['parser'] = parser
        self.setup_dict = kwargs
        self.setup_dict['descendants'] = list([WebTag(_) for _ in self.soup.descendants if isinstance(_, BsTag)])

    def find_all(self, tag_name: str = '', *argv, **attrs) -> List[WebTag]:
        """
        Find all children tags by tag_name and possible partial key-values
        :param tag_name: children tag name, can be partial
        :param attrs: pairs with key-name, key names and values can be partial
        :return: list of WebTag
        """
        attrs = {} if attrs is None else attrs

        for arg in argv:
            if not isinstance(arg, dict):
                raise TypeError
            attrs.update(arg)    

        kv = [None] * 2
        if attrs:
            if len(attrs) == 1:
                kv = list(attrs.items())[0]
                return self.find_all_(tag_name, *kv)
            if len(attrs) > 1:
                print('len(attrs)>1', {'tag_name': tag_name, 'attrs': attrs})
                return self.find_at({tag_name: ''}, {'tag_name': tag_name, 'attrs': attrs})
        return self.find_all_(tag_name, *kv)

    def find_all_(self,
                  partial_tag_name: str = '',
                  partial_key: str or None = None,
                  partial_value: str or None = None) -> List[WebTag]:
        """
        Allows find one or all matching tags using only some parts of its names (names of keys, partial values) what is
        helpful while iterating source code of pages which DOM is often modified by for instance by Javascript.
        :param partial_tag_name: full or partial name of xml/html tag
        :param partial_key: partial key name - instead of writing i.e. 'data-source' user can write 'data-'
        :param partial_value: as up, partial value, i.e: full 'http://example.com' - user can write 'example.com'
        """

        tags_found, counter = [], 0

        for next_tag in self.soup.find_all():
            try:
                if partial_tag_name in next_tag.name:

                    if not partial_key and not partial_value:
                        tags_found.append(WebTag(next_tag))
                        continue

                    for k, v in next_tag.attrs.items():
                        v = str(v)
                        if partial_key and partial_value:
                            if partial_key in k and partial_value in v:
                                tags_found.append(WebTag(next_tag))
                                break
                        elif partial_key is not None and partial_value is None:
                            if partial_key in k:
                                tags_found.append(WebTag(next_tag))
                                break
                        elif partial_key is None and partial_value is not None:
                            if partial_value in v:
                                tags_found.append(WebTag(next_tag))
                                break
                        elif partial_key is None and partial_value is None:
                            tags_found.append(WebTag(next_tag))
                            break
            except (TypeError, Exception) as ex:
                print('Catched exception: ', type(ex), 'at tag:', next_tag)

        return tags_found

    def find_at(self,
                root_tag: dict,
                children: Tuple[dict] or List[dict]) -> List[WebTag]:
        """
        Allows to find all children tags in root tag
        :param root_tag: dict with partial tag_name and sub-dict with attrs (key names binded to values)
        :param children: one dict or tuple/list with dicts, passing other types will raise TypeError. Check query_dict
            function for more information about passing dicts to WebTag/WebSalad methods
        :return: list of WebTag that are children of root_tag in hierarchy of this WebSalad instance
        """

        if not isinstance(root_tag, dict):
            raise TypeError
        if not isinstance(children, (list, tuple)):
            children = [children, ]

        root_tag = query_dict(root_tag)
        for index, ch in enumerate(children):
            if not isinstance(ch, dict):
                raise TypeError
            children[index] = query_dict(children[index])

        root_matches = []
        if root_tag['tag_name'] == '' and root_tag['attrs'] == {}:
            root_matches = [WebTag(_) for _ in self.soup.find_all()]
        if root_tag['tag_name'] != '' and root_tag['attrs'] == {}:
            tag_name = root_tag['tag_name']
            root_matches = [WebTag(_) for _ in self.soup.find_all() if tag_name in _.name]
        if root_tag['tag_name'] != '' and root_tag['attrs'] != {}:
            tag_name = root_tag['tag_name']
            root_matches = [WebTag(_) for _ in self.soup.find_all() if tag_name in _.name]

            attr_matches = []
            for wt in root_matches:
                all_pair_matches = True
                for k, v in root_tag['attrs'].items():
                    if not wt.has_key_value(k, v):
                        all_pair_matches = False
                        break
                if all_pair_matches:
                    attr_matches.append(wt)
            root_matches = attr_matches

        to_iter = []
        for wt in root_matches:
            to_iter.extend(WebTag(_) for _ in Soup(str(wt), 'html.parser').find_all() if isinstance(_, BsTag))

        result = []
        for next_match in to_iter:
            for next_child in children:
                if next_child['tag_name'] in next_match.name:
                    if next_match.has_all_keys_values(**next_child['attrs']):
                        result.append(next_match)
                        break
        return result

    find_children_of = find_at

    def find_by_xpath(self, xpath: str) -> List[WebTag]:
        """
        Allows to use XPath expression, enhancement, BeautifulSoup has not this functionality ;-)
        See for more: https://www.w3schools.com/xml/xpath_syntax.asp
        :param xpath: str Xpath expression
        :return: list of WebTag
        """
        result = []
        for next_match in html.fromstring(str(self)).xpath(xpath):
            result.extend(self.soup.find_all(name=next_match.tag, attrs={k: v for k, v in next_match.attrib.items()}))

        return list(WebTag(_) for _ in result if isinstance(_, BsTag))

    def to_web_tags(self) -> List[WebTag]:
        """
        :return: list of WebTags
        """
        return list(WebTag(_) for _ in self.soup.find_all())

    def get_soup(self, as_copy=True) -> Soup:
        """
        Get a copy of internal bs4.BeautifulSoup instance
        :return: bs4.BeautifulSoup
        """
        if as_copy:
            return deepcopy(self.soup)
        return self.soup

    def copy(self) -> WebSalad:
        """
        Get a copy of this instance
        :return:
        """
        return deepcopy(self)

    def run_bs4_method(self, bs4_method_name='find_all', *args, **kwargs) -> Any:
        """
        Allows to run bs4.BeautifulSoup method on internal object.
        :param bs4_method_name: method of bs4.BeautifulSoup object
        :param args: to be passed to method
        :param kwargs: to be passed to method
        :return: result of invoking method. May raise exceptions!
        """
        if hasattr(self.soup, bs4_method_name):
            bs4_method_name = getattr(self.soup, bs4_method_name)
            if callable(bs4_method_name):
                return bs4_method_name(*args, **kwargs)
        raise TypeError(f'bs4.BeautifulSoup object has not callable attribute "{bs4_method_name}"')

    def get_bs4_methods(self, private=False, protected=False) -> List[str]:
        """
        Gets methods of bs4.BeautifulSoup object
        :param private: set to True for private also methods
        :param protected: set to True for also orotected methods
        :return: list of method names
        """
        methods = [_ for _ in dir(self.soup) if callable(getattr(self.soup, _))]
        if not protected:
            methods = [_ for _ in methods if not _.startswith('__')]
        if not private:
            methods = [_ for _ in methods if not _.startswith('_')]
        return list(methods)

    def prettify(self, encoding=None, formatter="minimal") -> str:
        """
        Returns styled HTML code
        :param encoding: check bs4 documentation
        :param formatter: check bs4 documentation
        :return: str with formatted code
        """
        return self.soup.prettify(encoding, formatter)

    def get_text(self) -> str:
        """
        Gets text of HTML tag (i.e. <a href='https://...'>some text</a>    ->   some text
        :return:
        """
        return self.soup.get_text()

    def __str__(self) -> str:
        return str(self.soup).replace('\n', '')

    def __repr__(self):
        return self.__str__()

    def __iter__(self):
        """
        Allows:  for web_tag in web_salad_instance: (...)
        :return: list_iterator over children of this instance
        """
        return iter(self.soup.find_all())

    def __contains__(self, item: WebTag or dict or str) -> bool:
        """
        Allows: web_tag/dict/str in web_salad_instance

        :param item: WebTag / dict / str value to check. If type of item is
            * str:     checks if str is in HTML code of WebSalad
            * dict:    methods turns it to WebTag object and then checks if similar child exists
            * WebTag:  look above
        :return: bool
        """
        if isinstance(item, WebTag):
            item = {
                'tag_name': item.name,
                'attrs': item.attrs
            }

        if isinstance(item, dict):
            item = query_dict(item)
            for _ in self.soup.find_all():
                if not isinstance(_, BsTag):
                    continue
                if item in WebTag(_):
                    return True
            return False
        if isinstance(item, str):
            return item in str(self.soup)
        raise TypeError

    def __rshift__(self, str_filename: str):
        open(str_filename, 'wb').write(bytearray(str(self).encode('utf8')))
        return True

# are we really made of stars?
