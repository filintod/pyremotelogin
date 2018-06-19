import io
import os
from lxml import etree as ET, html
import logging

__author__ = 'duran'

log = logging.getLogger(__name__)


def validate_xml_against_xsd(xml, xsd_file):
    """ Validates that a XML file is valid against a XML Schema file

    :param xml: an ElementTree or a string containing xml data
    :param xsd_file: path to an xsd file

    """
    xsd = ET.XMLSchema(ET.parse(xsd_file))
    try:
        return xsd.validate(xml if isinstance(xml, ET.ElementBase) else ET.fromstring(str(xml)))
    except:
        return False


def create_and_upload_xml_file(device, local_file_name, remote_file_name, xml_element_root):
    """  From an lxml object creates an xml file and upload to a server

    """
    log.info('Creating new XML file ' + local_file_name)
    new_file = open(local_file_name, 'w')
    new_file.write(ET.tostring(xml_element_root, pretty_print=True, encoding='utf-8'))
    new_file.close()

    log.debug('Sending a copy of the file to the RDU and overwriting the old pmg-profile.xml file')
    device.upload([local_file_name], [remote_file_name])


def lxml_text_content(element):
    """ gets the string contained inside this element node tree """
    return " ".join(x for x in element.itertext())


def pretty_print_xml(xml_string):
    """ Returns the xml string in a nicer format with tabs and new lines for easy reading

    """
    parser = ET.XMLParser(resolve_entities=False, strip_cdata=False)
    document = ET.fromstring(xml_string, parser)
    return ET.tounicode(document, pretty_print=True)


def retrieve_xml_elements(filename, xpath, dict_of_tags, normalize_path=None, name_attribute='IRTaskGroupName'):
    """ retrieves XML values from a simple xml document given a set of tags that we want the value from

    :param filename:
    :param xpath:
    :param dict_of_tags:
    :return:
    """
    ret = []
    try:
        with open(filename) as xml:
            tree = parse_xml(xml)

            try:
                # get root to get metadata information for name or if not found use the filename
                name = tree.get(name_attribute) or os.path.splitext(os.path.basename(filename))[0]
            except:
                name = ""

            # get information
            for task in tree.findall(xpath):
                # init values
                values = dict([(k, None) for k in dict_of_tags.values()])
                for e in task.iter():
                    if e.tag in dict_of_tags:
                        data = e.text.strip() if e.text else ""
                        if isinstance(dict_of_tags[e.tag], tuple):
                            if dict_of_tags[e.tag][1]:
                                values[dict_of_tags[e.tag][0]] = normalize_path(data) if data else ""
                            else:
                                elem = e.findall(dict_of_tags[e.tag][2])
                                values[dict_of_tags[e.tag][0]] = elem[0].get(dict_of_tags[e.tag][3]) if elem else None
                        else:
                            values[dict_of_tags[e.tag]] = data
                ret.append(values)

        return ret, name
    except IOError as e:
        raise IOError(e.args + (filename, ))


def encode_xml_text(text):
    # return the value without changing for non strings
    if not isinstance(text, str):
        return text
    text = text.replace("&", "&amp;")
    text = text.replace("\"", "&quot;")
    text = text.replace("'", "&apos;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def decode_xml_text(text):
    # return the value without changing for non strings
    if not isinstance(text, str):
        return text
    from html import unescape
    return unescape(text)


def xml_to_json(xml):
    import xmltodict
    import json
    return json.dumps(xmltodict.parse(xml))


class ElementBaseXpathStr(ET.ElementBase):
    """ an ElementBase with xpathbuilder friendly xpath method """
    def xpath(self, path, *args, **kwargs):
        return super(self.__class__, self).xpath(str(path), *args, **kwargs)


def parse_xml(xml_str_or_file, parser=None, **parser_kwargs):
    """ simple lxml parser to execute the correct parsing method and use ETree class as the default
        so we can use xpathbuilder directly without str casting

    Args:
        xml_str_or_file (str or IOBase):
        parser:
        **parser_kwargs:

    Returns:

    """
    if not parser:
        parser_lookup = ET.ElementDefaultClassLookup(element=ElementBaseXpathStr)
        parser = ET.XMLParser(**parser_kwargs)
        parser.set_element_class_lookup(parser_lookup)

    if isinstance(xml_str_or_file, str):
        return ET.fromstring(xml_str_or_file, parser=parser)
    elif isinstance(xml_str_or_file, bytes):
        return ET.parse(io.BytesIO(xml_str_or_file), parser=parser).getroot()
    elif hasattr(xml_str_or_file, 'read'):
        return ET.parse(xml_str_or_file, parser=parser).getroot()
    else:
        raise NotImplementedError('We only know how to parse string, bytes or file objects.  Use straight lxml methods')


def patch_htmlelement():
    # monkey patch HtmlElement for xpathbuilder
    if not hasattr(html.HtmlElement, '__patchedxp'):
        htmlxpath = html.HtmlElement.xpath
        html.HtmlElement.xpath = lambda self, path, *args, **kwargs: htmlxpath(self, str(path), *args, **kwargs)
        html.HtmlElement.__patchedxp = True


def parse_html(xml_str_or_file, **parser_kwargs):
    """ simple lxml html parser to execute correct parsing html method and use our custom HTMLTree element """
    patch_htmlelement()
    return parse_xml(xml_str_or_file, parser=html.html_parser, **parser_kwargs)