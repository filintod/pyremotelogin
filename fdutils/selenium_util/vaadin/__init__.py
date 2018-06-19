import logging
from functools import wraps

from fdutils.selenium_util import locator_utils
from fdutils.selenium_util import pageobject
from fdutils.xml import lxml_text_content
from .locators import *

log = logging.getLogger(__name__)


# information gathering
# rows of items


class VaadinPageObject(pageobject.PageObject):
    """ placeholder to define vaadin related actions on page object"""

    loc_loading_indicator = locator_utils.locator("css=div[class*=v-loading-indicator]")

    def item_from_menu_bar_list(self, sub_menu_item_name):
        """ when a submenu pops up a list after clicking a menu

        Args:
            sub_menu_item_name:

        Returns:

        """
        return self.get("//span[text()='{item_name}' and ./ancestor::div[contains(@class,'v-menubar-submenu')]]"
                        "".format(item_name=sub_menu_item_name))

    def item_from_list(self, item_name):
        """ combo box selection list """
        return self.get("//span[text()='{item_name}' and "
                        "./ancestor::*//div[contains(@class,'v-filterselect-suggestmenu')]]"
                        "".format(item_name=item_name))

    def _get_table_root_and_header_values(self, header_value, lower_case_headers=False):
        root = self.get_inner_html_as_xml(table_with_header_value(header_value, as_str=True))
        header_values = [lxml_text_content(e).strip() for e in root.xpath(table_header_tds(as_str=True))]
        if lower_case_headers:
            header_values = [v.lower() for v in header_values]
        return root, header_values

    def get_table_information(self, header_value, tables_of_inputs=False, lower_case_keys=False):

        table_return = []

        def fill_table_return(elements, f):
            _table_return = []
            has_values = False

            for i in range(len(elements) // header_values_len):
                current_index = i * header_values_len
                values = [f(e).strip() for e in elements[current_index:current_index + header_values_len]]
                if any(values):
                    has_values = True
                _table_return.append(dict(zip(header_values, values)))
            return _table_return, has_values

        root, header_values = self._get_table_root_and_header_values(header_value, lower_case_keys)
        header_values_len = len(header_values)
        any_value = False

        if not tables_of_inputs:
            table_return, any_value = fill_table_return(root.xpath(table_rows_tds(as_str=True)),
                                                        lambda e: lxml_text_content(e))

        if tables_of_inputs or not any_value:
            table_return, _ = fill_table_return(
                self.get_table_elements(header_value, only_rows=True, table_of_inputs=True),
                lambda e: e.get_attribute('value'))

        return table_return

    def upload_file(self, filepath, upload_button_label):
        self.get(locators.file_input_followed_by_button(upload_button_label, as_str=True)).enter_text(filepath)
        self.move_mouse_to_and_click(self.get(locators.button(upload_button_label, as_str=True)))

    def get_grid_information(self, grid_label_value):
        table = self.get_inner_html_as_xml(grid_locator_containing_label(grid_label_value, as_str=True))
        root = table.getroot()
        label_values = root.xpath("//div[contains(@class, 'v-label')]")
        ret = {}
        for label, value in [(label_values[i], label_values[i + 1]) for i in range(len(label_values) - 1)[::2]]:
            ret[label.text] = value.text

        return ret

    def get_table_elements(self, header_value, only_rows=False, table_of_inputs=False):
        table = self.get(table_with_header_value(header_value, as_str=True))
        elements = table.get_list(table_rows_input(as_str=True) if table_of_inputs else
                                  table_rows_tds(as_str=True))
        if only_rows:
            return elements
        else:
            headers = table.get_list(table_header_tds(as_str=True))
            return headers, elements

    def get_table_elements_as_dict(self, header_value, lower_case_keys=False):
        _, header_values = self._get_table_root_and_header_values(header_value, lower_case_keys)
        header_values_len = len(header_values)

        rows = self.get_table_elements(header_value, only_rows=True)
        ret = []
        if rows:
            for i in range(len(rows) // len(header_values)):
                current_index = i * header_values_len
                ret.append(
                    dict(zip(header_values, [e for e in rows[current_index:current_index + header_values_len]])))

        return ret

    def collapse_open_tree_node(self, node_name):
        self.click_element_at(self.get(tree_menu_node(node_name, as_str=True)), -5, 5)


def tree_menu(node, child=None):
    def menu_deco(f):
        wraps(f)
        def w(self: VaadinPageObject, *args, **kwargs):
            if child:
                child_object = self.get(tree_menu_child(node, child, as_str=True))
                if not child_object.is_displayed():
                    self.click_element_at(tree_menu_node(node, as_str=True), -5, 5)
                    child_object = self.get(tree_menu_child(node, child, as_str=True))

                child_object.click()
            else:
                self.click_element(tree_menu_node_caption(node, as_str=True))
            self.wait_for_loading_indicator_to_disappear()

            return f(self, *args, **kwargs)
        return w
    return menu_deco


class AuthenticatedVaadingPage(VaadinPageObject, pageobject.AuthenticatedPageObject):
    pass
