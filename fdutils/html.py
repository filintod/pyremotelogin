import logging
import re

from fdutils import strings
from fdutils.lists import ordered_dict
from fdutils.strings import cast

log = logging.getLogger(__name__)

MULTI_SPACES_re = re.compile(r'\s{2,}')
HTML_TABLE_NODES = 'thead tbody tfoot colgroup caption'.split()
HTML_TABLE_NODES_SELF = ['self::' + node for node in HTML_TABLE_NODES]


def _parse_input_value(cell_child_elements):
    data = []
    for input_element in [c for c in cell_child_elements if c.tag in ('select', 'input')]:
        tag = input_element.tag.lower()
        if tag == 'select':
            for option in input_element.getchildren():
                if option.get('selected', False):
                    data.append(option.text.strip())
        else:
            if input_element.get('type') == 'text':
                data.append(input_element.value.strip())

    return data[0] if len(data) == 1 else data if len(data) > 1 else ''


def _get_strip_content(cell):
    return MULTI_SPACES_re.sub(' ', str(cell.text_content()).replace('&nbsp;', ' '))


def _get_row_label_cells_data(row):

    labels = []
    data = []

    list_of_cells = row.xpath('.//td|.//th')
    for cols in list_of_cells:
        children = cols.getchildren()
        if children and any([c.tag in ('select', 'input') for c in children]):
            t = _parse_input_value(children)
        else:
            t = _get_strip_content(cols).strip()

        if t:
            td_attrib = dict(cols.items())
            td_value = dict(attrib=td_attrib, txt=t)

            if cols.tag == 'th':
                labels.append(td_value)

            else:
                data.append(td_value)

    for structure in (labels, data):
        if not any([d['txt'] for d in structure]):
            del structure[:]

    return labels, data


def _get_tbody_rows(table):
    return (table.xpath('tbody/tr|tr') or
            table.xpath('*[not ({})]/tr'.format(' or '.join(HTML_TABLE_NODES_SELF)))
            )


def _remove_attributes(labels, rows):
    def _remove(data):
        ret = []
        for d in data:
            ret.append(d.get('txt', ''))
        return ret

    for i, label in enumerate(labels):
        labels[i][0] = _remove(label[0])

    for i, row in enumerate(rows):
        rows[i] = _remove(row)

    return labels, rows


def _normalize_rows(rows):
    max_cols = max([len(r) for r in rows])
    for i, row in enumerate(rows):
        if len(row) < max_cols:
            rows[i] = row + [''] * (max_cols - len(row))
    return rows


def _transpose_table_info(labels, rows):

    rows_t = [list(a) for a in zip(*_normalize_rows(rows))]
    labels_t = rows_t.pop(0)
    for i, label in enumerate(labels[1:]):
        rows_t[i].insert(0, label)

    return labels_t, rows_t


def parse_html_table(table, keep_attributes=False, transpose=False):
    """ parses a regular html table
    
        where the headers are on top and the data is on each row, with
        one value per header column
        
    """
    labels = []
    rows = []

    thead_row = table.xpath('thead/tr')

    if thead_row:
        for row in thead_row:
            _row_labels, data = _get_row_label_cells_data(row)
            if data:
                log.debug('received data in thead?? ' + str(data))
            labels.append([_row_labels, 0])

    for row in _get_tbody_rows(table):

        _row_labels, row_data = _get_row_label_cells_data(row)

        if _row_labels:

            if not labels or (len(labels[-1][0]) > 1 and len(_row_labels) > 1):
                labels.append([_row_labels, len(rows)])

            else:
                row_data.insert(0, _row_labels[0])

        if row_data and all:
            rows.append(row_data)

    if not keep_attributes:
        labels, rows = _remove_attributes(labels, rows)

    if transpose:
        if len(labels) > 1:
            raise Exception('We have not implemented transposing tables with sub-labels inside')
        labels, rows = _transpose_table_info(labels[0][0], rows)

    elif len(labels) == 1:
        labels = labels[0][0]

    return labels, rows


def parse_html_table_row_headers(table, split_section_func=None, keep_attributes=False):
    """ parses a table where the headers are on the rows
    
    Args:
        table (lxml ETree):
        split_section_func: 
        keep_attributes: 

    Returns:

    """
    sections = ordered_dict()

    section_name = ''

    for row in _get_tbody_rows(table):

        labels, data = _get_row_label_cells_data(row)

        if labels:
            # expecting only one columns
            labels = labels[0]
            data = data[0] if data else {}

            if split_section_func is not None:
                _section_name = split_section_func(labels, data, sections)

                if _section_name:
                    section_name = _section_name
                    continue

            elif section_name not in sections:
                sections[section_name] = {}

            sections[section_name][labels['txt']] = data

    if not keep_attributes:
        for section, section_dict in sections.items():
            for label, data in section_dict.items():
                section_dict[label] = data.get('txt', '')

    return sections if section_name else sections['']


def _create_from_table(labels, rows, row_names=(), cast_types=(int, float, str), as_list=False, key_format=None):
    """ given labels and rows creates a dictionary
        where each row is zipped with labels
    """
    ret = ordered_dict() if not as_list else list()
    labels = [l for l in labels if l]
    row_names = row_names or [r[0] for r in rows]
    max_rows_length = max(len(r) for r in rows)
    all_rows_same = all(len(r) == max_rows_length for r in rows)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            row[j] = cast(v, *cast_types)

        if max_rows_length != len(labels):
            data = dict(zip(labels, row[len(row) - len(labels):]))
        elif len(labels) == 2:
            data = row[-1] if len(row) == 2 else None
        elif all_rows_same:
            data = dict(zip(labels, row))
        else:
            data = dict(zip(labels[1:], row[len(row[1:]) - len(labels[1:]):]))

        if as_list:
            ret.append(data)
        else:
            key = key_format(row_names[i]) if key_format else row_names[i]
            ret[key] = data

    return ret


def create_dict_from_table(labels, rows, row_names=(), cast_types=(int, float, str), key_format=None):
    return _create_from_table(labels, rows, row_names, cast_types, False, key_format=key_format)


def create_list_from_table(labels, rows, row_names=(), cast_types=(int, float, str)):
    return _create_from_table(labels, rows, row_names, cast_types, True)


def parse_table_mix_columns(t_labels, t_rows, info_labels, cast_types=(int, str)):
    """ parses the information contained in a table where there can be one header and sub-header
        
        I'm only taking into account one header and one sub-header
        a more general case could be built but that is not my problem at the moment
    """

    cast = lambda v: strings.cast(v, *cast_types)

    labels = [l[0] for l in info_labels]
    sub_labels = [l[1] for l in info_labels] if len(t_labels) > 1 else []

    info = ordered_dict()
    for i, label in enumerate(labels):
        info[label] = ordered_dict()
        for sub_label in sub_labels[i]:
            info[label][sub_label] = ordered_dict()

    t_labels = t_labels[1]

    on_header_section = True

    for i, row in enumerate(t_rows):
        title = row.pop(0)

        if i == t_labels[1]:
            on_header_section = False

        sub_label_count = 0

        for label_index, label in enumerate(labels):

            if on_header_section:
                info[label][title] = cast(row[label_index])

            elif sub_labels:
                for sl, sub_label in enumerate(sub_labels[label_index]):
                    info[label][sub_label][title] = cast(row[sub_label_count])
                    sub_label_count += 1

    return info
