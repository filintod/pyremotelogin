import collections
import logging

from fdutils.exceptions import ElementNotUniqueError

log = logging.getLogger(__name__)


def setdefault(*dicts, **defaults):
    """ create a new dict by updating parameters not present of previous dictionary

        Usage:
            d1 = dict(a=1, b=2)
            d2 = dict(b=3, c=4)
            d3 = dict(c=3, e=5)

            d4 = setdefault(d1, d2, d3)
            now d4 is equal to {'a': 1, 'b': 2, 'c': 4, 'e': 5}
            d1 values are not updated, then d2 new values (c=4) is not updated by d3, and so on

    :param default_parameters:
    :param parameters:
    :return:
    """
    param_complete = dict(dicts[0])
    for d in dicts[1:]:
        for k,v in d.items():
            param_complete.setdefault(k, v)

    for k,v in defaults.items():
        param_complete.setdefault(k, v)

    return param_complete


def setdefault_inplace(*dicts, **defaults):
    """ similar to setdefault above but updating the first dictionary in the list instead of returning a new one

    :param default_parameters:
    :param parameters:
    :return:
    """
    for d in dicts[1:]:
        for k,v in d.items():
            dicts[0].setdefault(k, v)

    for k,v in defaults.items():
        dicts[0].setdefault(k, v)


def is_sequence(arg):
    return (arg is not None and not isinstance(arg, str) and
            (isinstance(arg, collections.Sequence) or isinstance(arg, collections.Mapping)))


def is_list_or_tuple(data):
    return data is not None and isinstance(data, collections.Sequence) and not isinstance(data, str)


def to_sequence(arg, seq_type=None):
    """ function to check if arg is a sequence and if not return it as a sequence of type defined by seq_type, also
        if the arg is a sequence and the seq_type is different to the arg type change the arg type to seq_type

    :param arg: a sequence or arbitrary basic element (int, str, etc.) that we want to check
    :param type seq_type: one of either dict, list or tuple. If other value we will set the sequence as list

    """
    def return_type(t):
        if t:
            if t is tuple:
                return (arg, ) if arg else tuple()
            elif t is dict:
                return {arg: True} if arg else dict()
            elif t is set:
                return {arg, } if arg else set()
        return [arg] if arg else list()

    if not is_sequence(arg):
        return return_type(seq_type)

    elif seq_type is not None and type(arg) is not seq_type:
        return seq_type(arg)

    return arg


def _add_elements_to_list(original_list, elements, condition, count, unique, raise_exception_if_not_unique):
    """ general private utility adds elements to the list x
        if unique is True it will only add it if it does not exists before (like a set) or if the lambda function is true

    :param list original_list: list where we would remove the elements from
    :param list or None elements: list of element to find in l and remove
    :param condition: lambda function to compare and. Either this is used or elements is used
    :param int count: number of times an element can be repeated. 0 means all the times
                            This function does not keep a counter for every element in elements, so this counter is for
                            all removals. We'll add the functionality If we see a need to have it

    :rtype: int
    :return: number of elements added

    """

    add_counter = 0
    if not original_list or (not elements and not condition):
        return 0

    if unique:
        if condition is None:
            add_me = lambda v: v not in elements
        else:
            add_me = condition
    else:
        add_me = (lambda _: True)

    for v in original_list:
        if add_me(v):
            if not count or add_counter < count:
                original_list.append(v)
                add_counter += 1
        elif condition is None and raise_exception_if_not_unique:
            log.debug('Trying to add element ({}) but it is not unique'.format(v))
            raise ElementNotUniqueError

    return add_counter


def add_to_list(to_list, new_elements, unique=False, count=0, raise_exception_if_not_unique=False):
    return _add_elements_to_list(to_list, new_elements, None, count, unique, raise_exception_if_not_unique)


def add_to_list_if_condition(to_list, elements, condition, unique=False, count=0, raise_exception_if_not_unique=False):
    return _add_elements_to_list(to_list, elements, condition, count, unique, raise_exception_if_not_unique)


def get_elements_in_list_if_condition(elements, condition, count=0, return_index=False):
    """

    :param list  elements:
    :param condition:  lambda function to compare
    :param int count: 0 = return all matches; if not just return the number of matches up to count
    :return: list of matches
    :rtype: list
    """
    ret = []
    current_count = 0
    for i, elem in enumerate(elements):
        if condition(elem):
            if return_index:
                ret.append(i)
            else:
                ret.append(elem)
            current_count += 1
            if count and current_count == count:
                break
    return ret


def _remove_elements_from_list(original_list, elements=None, condition=None, count=0):
    """ general private utility removes elements from the list x if elements exists or if the lambda function is true

    :param list original_list: list where we would remove the elements from
    :param list or None elements: list of element to find in l and remove
    :param condition: lambda function to compare and. Either this is used or elements is used
    :param int count: number of times to remove elements. Remove all if value is 0.
                            This function does not keep a counter for every element in elements, so this counter is for
                            all removals. We'll add the functionality If we see a need to have it

    :rtype: int
    :return: number of elements removed

    """

    j = 0
    remove_counter = 0
    if not original_list or (not elements and not condition):
        return 0

    delete_me = (lambda v: v in elements) if elements else condition

    for v in original_list:
        if delete_me(v) and (not count or remove_counter < count):
            remove_counter += 1
        else:
            original_list[j] = v
            j += 1

    del original_list[j:]
    return remove_counter


def del_from_list(l, elements, count=0):
    """ Delete elements from list

    :param list l: the list that we want to delete elements from
    :param list elements: list of elements to delete from l
    :param int count: (optional) number of times to remove element if they are repeated
    """
    return _remove_elements_from_list(l, elements, None, count)


def del_from_list_by_index(original_list, indexes, count=0):
    """ general private utility removes elements from the list x if elements exists or if the lambda function is true

    :param list original_list: list where we would remove the elements from
    :param list or None indexes: list of element to find in l and remove
    :param int count: number of times to remove elements. Remove all if value is 0.
                            This function does not keep a counter for every element in elements, so this counter is for
                            all removals. We'll add the functionality If we see a need to have it

    :rtype: int
    :return: number of elements removed

    """

    j = 0
    remove_counter = 0
    if not original_list or not indexes:
        return 0

    for i, v in enumerate(original_list):
        if remove_counter < count and i in indexes:
            remove_counter += 1
        else:
            original_list[j] = v
            j += 1

    del original_list[j:]
    return remove_counter


def del_elements_in_list_if_condition(l, condition, count=0):
    """ Delete elements from list if a lambda condition is given (i.e. lambda (element): element > value)

    :param list l: the list that we want to delete elements from
    :param lambda condition: lambda function to compare
    :param int count: (optional) number of times to remove element if they are repeated
    """
    return _remove_elements_from_list(l, None, condition, count)


def ordered_dict(*args, **kwargs):
    """ helper to return an ordered dictionary depending on python version by using the straight dictionary of
        python 3.6 that is ordered or collections.ordereddict if less than 3.6
    """
    import sys
    if sys.version_info >= (3, 6):
        return dict(*args, **kwargs)
    else:
        import collections
        return collections.OrderedDict(*args, **kwargs)


def sort_nested_dict_generator(sort_me, item_key, start_return=0, count=0, condition=lambda x: x, reverse=False):
    counter = 0
    for key in sorted(sort_me.keys(), key=lambda x: condition(sort_me[x][item_key]), reverse=reverse):
        counter += 1
        if start_return and counter < start_return:
            continue
        if count and count < counter:
            return
        yield (key, sort_me[key])


def sort_nested_dict(sort_me, item_key, start_return=0, count=0, condition=lambda x: x, descending=False):
    """ return a list of tuples (key, dictionary value) sorted by an element in the nested dictionary.
        A nested dictioanry is any of dict(dict), dict(list), or dict(tuple), or any sequence class that implements __getitem__ method

    :param dict sort_me: a dictionary-like object to sort
    :param str or int item_key: this value point to the dictionary key or the list/tuple index of the nested component
    :param int start_return: from what point to return the values from
    :param int count: if > 0 it will iterate only for the amount of items given here. If 0, it will iterate over all
    :param function condition: a function to call to evaluate the item_key value. ie. sort by the length of the third element: sort_nested_dict(d, 3, lambda_on_value=lambda x: len(x))
    :param bool descending: flag to sort ascending or descending
    :return: a list of tuples of type (sort_me key, sort_me_value)
    :rtype: list of tuple

    """
    counter = 0
    ret = list()
    for key in sorted(sort_me.keys(), key=lambda x: condition(sort_me[x][item_key]), reverse=descending):
        counter += 1
        if start_return and counter < start_return:
            continue
        if count and count < counter:
            break
        ret.append((key, sort_me[key]))
    return ret


def list_to_matrix_index_generator(values, rows=None, columns=None, row_order=True):
    """  Generates rows of elements from the list of values.

         The values can be in row or column order meaning that if we get 1,2,3,4,5,6 with rows=2 and row order=True
         then we will generate [1,2,3],[4,5,6], but for row_order=False we will generate [1,3,5],[2,4,6] as it will
         be in column order

    """
    import math

    values_length = len(values)

    if rows is None and columns is None:
        raise ValueError('You need to define the rows or the columns or both')

    if rows and columns and (rows * columns) < values_length:
        raise ValueError('The number of rows by columns does not match the number of elements in values')

    num_cols = columns
    num_rows = rows

    if rows is None:
    # fixed number of columns
        num_rows = int(math.ceil(values_length / columns))
    elif columns is None:
        num_cols = int(math.ceil(values_length / rows))

    if row_order:
        for i in range(num_rows):
            index = i * num_cols
            yield values[index: index + num_cols]
    else:
        for i in range(num_rows):
            index = i
            yield values[index: values_length: num_rows]           


def print_in_columns(values, columns=5, column_width=20, center=True, row_order=False):    
    
    # one liner lambda function to format a variable v with centered alignment and column_width width
    align = '^' if center else '<'
    string_format = lambda v: '{v:{align}{column_width}}'.format(v=v, align=align, column_width=column_width)
    
    for row_values in list_to_matrix_index_generator(values, columns=columns, row_order=row_order):        
                
        # using the string join function to put together elements in a sequence 
        # created using an iterator implicitly with map that takes every element from a sequence
        # and executes a function on it 
        print(' | '.join(map(string_format, row_values)))        


def flatten(list_of_list):
    l = []
    list(l.extend(row) for row in list_of_list)
    return l
