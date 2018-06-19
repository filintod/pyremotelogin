import collections

from IPython.display import display
from IPython.display import HTML
from sqlalchemy.engine import ResultProxy


def print_html_table(title, data, column_names=()):
    """ prints an HTML formatted table to a jupyter output

    Args:
        title:
        data (dict or list):
        column_names:

    Returns:

    """
    table = list("<table style='width=100%'><caption>{title}</caption>".format(title=title))

    if isinstance(data, collections.Mapping):
        rows = data.values()
        columns = column_names or data.keys()
    elif isinstance(data, ResultProxy):
        rows = data
        columns = column_names or data.keys()
    else:
        rows = data
        columns = column_names

    # add title
    table.append('<tr>')
    for k in columns:
        table.append("<th style='text-align: center'>{k}</th>".format(k=k))
    table.append('</tr>')

    # add rows
    for row in rows:
        table.append('<tr>')
        for data in row:
            table.append('<td style=\'valign: top\'>{data}</td>'.format(data=data))
        table.append('</tr>')
    table.append("</table>")

    # finally display
    display(HTML(''.join(table)))
