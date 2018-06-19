from fdutils import xpathbuilder as xp
root = xp.root
_ = xp._


def s(builder, expect):
    assert str(builder) == expect


def test_all_namespace():
    # xpath with namespace
    xpns = xp.XPNS('atom')
    s(xp.all_tr.where(xp._all_td._t('#^InternetGatewayDevice.LANDevice')),
      '//tr[.//td[starts-with(normalize-space(text()), "InternetGatewayDevice.LANDevice")]]')

    s(xp.all_td("Phone Number").nexts_td["{0}"],
      '//td[.="Phone Number"]/following-sibling::td[{0}]')

    TRANSLATE = 'translate({}, "ABCDEFGHIJKLMNOPQRSTUVWXYZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸŽŠŒ", '\
      '"abcdefghijklmnopqrstuvwxyzàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿžšœ")'
    TRANSLATE_STR = TRANSLATE.format('@value')
    TRANSLATE_NORM = TRANSLATE.format('normalize-space(.)')
    TRANSLATE_ID = TRANSLATE.format('@id')

    s(xpns.all_entry.where(xpns.all_category._term('person')).title,
      '//atom:entry[//atom:category[@term="person"]]/atom:title')

    s(xpns.all_entry.where(xpns.all_category._term('person')).contributor.email,
      '//atom:entry[//atom:category[@term="person"]]/atom:contributor/atom:email')

    s(xpns.all_entry.where(xpns.all_category._text('&person')).contributor.email,
      '//atom:entry[//atom:category[{}="person"]]/atom:contributor/atom:email'.format(TRANSLATE.format('text()')))

    # using _t instead of _text
    s(xpns.all_entry.where(xpns.all_category._t('&person')).contributor.email,
      '//atom:entry[//atom:category[{}="person"]]/atom:contributor/atom:email'.format(TRANSLATE.format('text()')))

    s(xpns.root.all_table(id="hrsDtlTbl").all_tr[2].all_td(style='!^display : none', id='^regHrsDataTD'),
      '//atom:table[@id="hrsDtlTbl"]//atom:tr[2]//atom:td[not(starts-with(@style, "display : none")) and starts-with(@id, "regHrsDataTD")]')

    s(xp.any._t.startswith('^hello'), '//*[starts-with(text(), "hello")]')
    expect = './/table[tr/td[.="hello"]]'
    s(_.all('table').where('tr/td[.="hello"]'), expect)
    s(_.all_table.where('tr/td[.="hello"]'), expect)
    s(_.all_table.where(_.tr.td('hello')), expect)
    s(_.all_table.where(_.tr.td('^hello')), './/table[tr/td[starts-with(., "hello")]]')
    s(_.descendants('table').where('tr/td[.="hello"]'), expect)

    # id property
    s(_.all_table.where(_.tr.td._text("hello"))._id,
      './/table[tr/td[text()="hello"]]/@id')
    s(_.all_table.where(_.tr.td("hello"))._id,
      './/table[tr/td[.="hello"]]/@id')

    # s(_.all_table.where(_.tr.td("hello")).and_id('myid'),
    #   './/table[tr/td[.="hello"]]/.[@id="myid"]')

    print(xp.any._("*Broadband Connection").next())
    print(xp.all_table._class('status-table').all_input._value('(?i)Restart')._type('submit'))
    print(xp.all_div("(?i)Home Network Devices").next_table[1])
    print(xp.any.div._.strip().eq('(?i)timed statistics'))

    # normalize-space
    x = xp.anystrip
    print(x.eq("(?i)Timed Statistics").next_table[1])
    s(x.eq("(?i)Statistics Time").previous_div[2],
      '//*[translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸŽŠŒ", "abcdefghijklmnopqrstuvwxyzàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿžšœ")="statistics time"]/preceding::div[2]')
    s(xp.anystrip("(?i)Broadband Connection").next_,
      '//*[translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸŽŠŒ", "abcdefghijklmnopqrstuvwxyzàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿžšœ")="broadband connection"]/following::*')
    s(xp.any._("#&Broadband Connection").next_,
      '//*[translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸŽŠŒ", "abcdefghijklmnopqrstuvwxyzàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿžšœ")="broadband connection"]/following::*')
    s(xp.anystrip.eq('Hello').next_table[1],
      '//*[normalize-space(.)="Hello"]/following::table[1]')
    #print(xp.anystrip[1])
    print(xp('//td')._endswith('(?i)hello'))

    print(xp.any._t('^1','$2','*3','4', insensitive=True))
    print(xp.any._t('^1')._t('$2')._t('*3')._t('4'))

    s(xp('//td')._endswith('hello'),
      '//td["hello"=substring(., string-length(.) - string-length("hello") + 1)]')

    s(xp.all_input._.re('^Hello', 'i').next()[1],
      '//input[re:test(., "^Hello", "i")]/following::*[1]')

    s(xp.all_input._endswith('Hello').next()[1],
      '//input["Hello"=substring(., string-length(.) - string-length("Hello") + 1)]/following::*[1]')

    s(xp.all_input._type('submit').and_value('(?i)Save')[1],
      '//input[@type="submit" and {}="save"][1]'.format(TRANSLATE_STR))
    s(xp.all_input._type('submit').and_value('&Save')[1],
      '//input[@type="submit" and {}="save"][1]'.format(TRANSLATE_STR))
    s(xp.all_input._type('submit')._value('(?i)Save')[1],
      '//input[@type="submit" and {}="save"][1]'.format(TRANSLATE_STR))
    s(xp.all_input._type('submit')._value('&Save')[1],
      '//input[@type="submit" and {}="save"][1]'.format(TRANSLATE_STR))
    s(xp.all_input._type.eq('submit')._value.eq_i('Save')[1],
      '//input[@type="submit" and {}="save"][1]'.format(TRANSLATE_STR))

    s(xp.all_input._value.eq_i('Clear Statistics'),
      '//input[{}="clear statistics"]'.format(TRANSLATE_STR))
    s(xp.all_input._value('(?i)Clear Statistics'),
      '//input[{}="clear statistics"]'.format(TRANSLATE_STR))

    # normalize-space (strip)
    s(xp.anystrip.starts_with('Home Network Devices').next_input._type('submit')[1],
      '//*[starts-with(normalize-space(.), "Home Network Devices")]/following::input[@type="submit"][1]')
    # normalize-space (strip) case insensitive
    s(xp.anystrip.starts_with('(?i)Home Network Devices').next_input._type('submit')[1],
    '//*[starts-with({}, "home network devices")]/following::input[@type="submit"][1]'.format(TRANSLATE_NORM))
    s(xp.anystrip.startswith_i('Home Network Devices').next_input._type('submit')[1],
    '//*[starts-with({}, "home network devices")]/following::input[@type="submit"][1]'.format(TRANSLATE_NORM))

    s(root.all().text()._contains('abc').ancestors().where(_.div | _.table)[1].render(),
      '//text()[contains(., "abc")]/ancestor::*[((div) or (table))][1]')

    s(root.all()._.text('abc').ancestors().where(_.div | _.table)[1].render(),
      '//*[text()="abc"]/ancestor::*[((div) or (table))][1]')

    s(root.all()._.text('abc').ancestors().where(_.div | _.table)[1].render(),
      '//*[text()="abc"]/ancestor::*[((div) or (table))][1]')

    s(root.all()._.text('(?i)aBc').ancestors().where(_.div | _.table)[1].render(),
      '//*[{}="abc"]/ancestor::*[((div) or (table))][1]'.format(TRANSLATE.format('text()')))
    # using t instead of text
    s(root.all()._.text('(?i)aBc').ancestors().where(_.div | _.table)[1].render(),
      '//*[{}="abc"]/ancestor::*[((div) or (table))][1]'.format(TRANSLATE.format('text()')))

    s(root.any._text('(?i)^aBc').ancestors().where(_.div | _.table)[1].render(),
      '//*[starts-with({}, "abc")]/ancestor::*[((div) or (table))][1]'.format(TRANSLATE.format('text()')))
    s(root.all()._.text('&^aBc').ancestors().where(_.div | _.table)[1].render(),
      '//*[starts-with({}, "abc")]/ancestor::*[((div) or (table))][1]'.format(TRANSLATE.format('text()')))
    s(root.all()._.text('^&aBc').ancestors().where(_.div | _.table)[1].render(),
      '//*[starts-with({}, "abc")]/ancestor::*[((div) or (table))][1]'.format(TRANSLATE.format('text()')))
    s(root.all()._.text('&$aBc').ancestors().where(_.div | _.table)[1].render(),
      '//*[substring(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸŽŠŒ", '
      '"abcdefghijklmnopqrstuvwxyzàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿžšœ"), string-length(translate(text(), '
      '"ABCDEFGHIJKLMNOPQRSTUVWXYZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸŽŠŒ", '
      '"abcdefghijklmnopqrstuvwxyzàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿžšœ")) '
      '- string-length("abc") + 1)="abc"]/ancestor::*[((div) or (table))][1]')


    s(root.all()._class.render(), '//@class')

    s(root.all_.text().where(_.ancestors('foo').where(_.bar._attr('var'))).render(),
      '//text()[./ancestor::foo[bar[@attr="var"]]]')

    s(root.all_.text().where(_.ancestors('foo').where(_.bar(attr='var'))).render(),
      '//text()[./ancestor::foo[bar[@attr="var"]]]')

    s(root.all_table.where('tr/td="hello"'),
      '//table[tr/td="hello"]')

    s(root.all_table.where('tr/td!="hello"').render(),
      '//table[not(tr/td="hello")]')

    s(root.all_table.where('tr/td!="hello"').all_tr.render(),
      '//table[not(tr/td="hello")]//tr')

    s(root.all_table.where('tr/td!="hello"').all('tr')[5].render(),
      '//table[not(tr/td="hello")]//tr[5]')

    s(root.all_table.where('tr/td!="hello"').or_id.contains('hello').render(),
      '//table[not(tr/td="hello") or contains(@id, "hello")]')

    # or_id == or_['id'].  the property id can be access both ways
    s(root.all('table').where('tr/td!="hello"').or_id.contains('hello').render(),
      '//table[not(tr/td="hello") or contains(@id, "hello")]')

    # without "or" preceding "_" then it is and "and" operation if there was a predicate before
    s(root.all('table').where('tr/td!="hello"')._id.contains('hello').render(),
      '//table[not(tr/td="hello") and contains(@id, "hello")]')

    # same as previous but with explicit and
    s(root.all('table').where('tr/td!="hello"').and_id.contains('hello').render(),
      '//table[not(tr/td="hello") and contains(@id, "hello")]')

    # or just an equality if not
    s(root.all('table')._['id'].contains('hello').render(),
      '//table[contains(@id, "hello")]')

    s(root.all('table').where('tr/td!="hello"').or_id.contains_i('hello').render(),
      '//table[not(tr/td="hello") or contains({}, "hello")]'.format(TRANSLATE_ID))

    s(root.all('table').where('tr/td!="hello"').or_id.contains_i('hello').render(),
      '//table[not(tr/td="hello") or contains({}, "hello")]'.format(TRANSLATE_ID))

    s(root.all('table').where('tr/td!="hello") or contains(@id, "hello"').render(),
      '//table[not(tr/td="hello") or contains(@id, "hello")]')

    s(root.all('table').where('not(tr/td="hello") or contains(@id, "hello")').render(),
      '//table[not(tr/td="hello") or contains(@id, "hello")]')

    s(root.all('table').where('tr/td!="hello"').or_id.not_contains_i('hello').or_.contains('perro').render(),
      '//table[not(tr/td="hello") or not(contains({}, "hello")) or contains(., "perro")]'.format(TRANSLATE_ID))

    s(root.all_table.where('tr/td!="hello"').or_id.not_contains('(?i)hello').count(),
      'count(//table[not(tr/td="hello") or not(contains({}, "hello"))])'.format(TRANSLATE_ID))

    s(root.all_table.where('tr/td!="hello"').or_id.not_contains('(?i)hello').pos(),
      'pos(//table[not(tr/td="hello") or not(contains({}, "hello"))])'.format(TRANSLATE_ID))

    s(root.all('table').where(_.tr.td._.ne("hello") | _._id.ne('hello')).render(),
      '//table[((tr/td[not(.="hello")]) or ((not(@id="hello"))))]')

    s(root.all('table').where(_.tr.td._.eq("hello") | _._id.ne('hello')).render(),
      '//table[((tr/td[.="hello"]) or ((not(@id="hello"))))]')

    s(root.all('table')._id.eq("hrsDtlTbl").all('tr')[2].all('td')._style.not_starts_with('display : none')._id.starts_with('regHrsDataTD').render(),
      '//table[@id="hrsDtlTbl"]//tr[2]//td[not(starts-with(@style, "display : none")) and starts-with(@id, "regHrsDataTD")]')

    # shorter version using value modifiers
    s(root.all_table(id="hrsDtlTbl").all_tr[2].all_td._style('~^display : none')._id('^regHrsDataTD'),
      '//table[@id="hrsDtlTbl"]//tr[2]//td[not(starts-with(@style, "display : none")) and starts-with(@id, "regHrsDataTD")]')

    # even shorter using attributes as kwargs to nodes
    s(root.all_table(id="hrsDtlTbl").all_tr[2].all_td(style='~^display : none', id='^regHrsDataTD'),
      '//table[@id="hrsDtlTbl"]//tr[2]//td[not(starts-with(@style, "display : none")) and starts-with(@id, "regHrsDataTD")]')

    s(root.all('table')._id.eq("hrsDtlTbl").all('tr')[2].all('td')._style.not_starts_with('display : none')._id.starts_with('regHrsDataTD').render(),
      '//table[@id="hrsDtlTbl"]//tr[2]//td[not(starts-with(@style, "display : none")) and starts-with(@id, "regHrsDataTD")]')

    s(root.all('div')._.starts_with("IP Operations & Services").ancestors('tr/td')[3].render(),
      '//div[starts-with(., "IP Operations & Services")]/ancestor::tr/td[3]')

    s(root.all('div')._.starts_with("IP Operations & Services").ancestors('tr').td[3].render(),
      '//div[starts-with(., "IP Operations & Services")]/ancestor::tr/td[3]')

    s(root.all_div.parent().where(~ _._id | _.to_number().ceil().lower().gt(5) | _('perro').node_name.eq("perro")).render(),
      '//div/..[((((not(./@id)) or (({} > 5)))) or ((.="perro" and local-name((.="perro"))="perro")))]'
      ''.format(TRANSLATE.format('ceiling(number(.))')))

    # apply multiple attributes to value
    button = xp.all_button
    attr = dict(value='value', disabled='disabled', name='name')
    for a, v in attr.items():
        button = button._[a](v)
    s(button, '//button[@value="value" and @disabled="disabled" and @name="name"]')

    # apply multiple attributes to value
    button = xp.all_button(value='value', disabled='disabled', name='name')
    s(button, '//button[@value="value" and @disabled="disabled" and @name="name"]')

    # apply no attributes to value
    button = xp.all_button()
    s(button, '//button')

    button = xp.all_button
    s(button, '//button')

    # case insensitive
    button = xp.all_button
    for a, v in attr.items():
        button = button._[a]('(?i)' + v)
    s(button, '//button[{value}="value" and {disabled}="disabled" and {name}="name"]'
              ''.format(value=TRANSLATE.format('@value'), disabled=TRANSLATE.format('@disabled'),
                        name=TRANSLATE.format('@name')))


