#!python3
# coding=utf8

import argparse
import functools
import re
import shutil
import string
import sys
import traceback


### CONFIGURATION

parser = argparse.ArgumentParser(description='Translates Appraisal blocks.')
parser.add_argument('input', nargs='?', default='./input.txt',
        help='Japanese input file')
parser.add_argument('output', nargs='?', default='./output.txt',
        help='English output file')
parser.add_argument('--dictionary', nargs='?', default='./dictionary.txt',
        help='Location of JP->EN dictionary of names')
parser.add_argument('--error_log', nargs='?', default='./errors.txt',
        help='Where to store errors')
parser.add_argument('--split_skills', action='store_true', default=False,
        help='Print skills one per line.')
parser.add_argument('--split_titles', action='store_true', default=False,
        help='Print titles one per line.')
parser.add_argument('--md', action='store_true', default=False,
        help='Output Markdown instead of plain text')
parser.add_argument('--print', action='store_true', default=False,
        dest='doprint', help='Only print to stdout instead of saving to file')
parser.add_argument('--update_dict', action='store_true', default=False,
        help='Alphabetize and write new words to the dictionary file. '
        'The old dictionary file is saved as a backup (.bak).')

args = parser.parse_args()

##### END OF CONFIGURATION



dictionary_header = """
# Add Japanese word first, then English word, line by line.
# Skills, titles, and names can go here.
""".strip();

missing_word_placeholder = '--NEEDS TRANSLATION--'

def translate_numbers(x):
    """Translate Japanese wide numbers to regular numbers."""
    x = re.sub("０", '0', x)
    x = re.sub("１", '1', x)
    x = re.sub("２", '2', x)
    x = re.sub("３", '3', x)
    x = re.sub("４", '4', x)
    x = re.sub("５", '5', x)
    x = re.sub("６", '6', x)
    x = re.sub("７", '7', x)
    x = re.sub("８", '8', x)
    x = re.sub("９", '9', x)
    return x

def read_dictionary_file():
    output = {}
    jp_line = True
    jp_word = None
    with open(args.dictionary, 'r') as dict_file:
        content = dict_file.readlines()
        for line in content:
            line = line.strip()
            if not len(line):
                continue
            if re.match('^\s*#', line):
                continue
            if jp_line:
                jp_word = line
            else:
                if line != missing_word_placeholder:
                    output[jp_word] = line.strip()
            jp_line = not jp_line
    return output

def dictionary_cmp(pair1, pair2):
    return cmp(pair1[1], pair2[1]) or cmp(pair1[0], pair2[0])

def write_dictionary_file(dictionary, missing_words):
    # Save old dictionary as backup.
    shutil.copy(args.dictionary, args.dictionary + '.bak')

    pairs = []
    for jp_word in missing_words:
        pairs.append((jp_word, missing_word_placeholder))
    for jp_word in dictionary:
        pairs.append((jp_word, dictionary[jp_word]))
    # Sort by English word, then Japanese
    pairs.sort(key=functools.cmp_to_key(dictionary_cmp))

    # Print to dictionary
    with open(args.dictionary, 'w+') as dict_file:
        dict_file.write(dictionary_header)
        dict_file.write('\n')
        for pair in pairs:
            dict_file.write(pair[0])
            dict_file.write('\n')
            dict_file.write(pair[1])
            dict_file.write('\n')


dictionary = read_dictionary_file()
missing_words = {}

def translate(word):
    """Tries to find translated word. Output as is otherwise."""
    word = re.sub('　', ' ', word)
    if word in dictionary:
        return dictionary[word.strip()]
    else:
        missing_words[word] = True
    return word

def read_plus_and_up(line, tag, output):
    plus_match = re.search('＋(\d+)', line)
    if plus_match:
        output[tag + '_plus'] = int(plus_match.group(1))
    up_match = re.search('\((\d+)up\)', line)
    if up_match:
        output[tag + '_up'] = int(up_match.group(1))

def match_attrib_2(lines, regex, tag, output):
    for line in lines:
        match = re.search(regex, line)
        if match:
            output[tag] = int(match.group(1))
            output[tag + '_max'] = int(match.group(2))
            read_plus_and_up(line, tag, output)
            return match

def match_attrib_1(lines, regex, tag, output):
    for line in lines:
        match = re.search(regex, line)
        if match:
            output[tag] = int(match.group(1))
            read_plus_and_up(line, tag, output)
            return match

def read_up_and_new(line, output):
    up_match = re.search('\((\d+)up\)', line)
    if up_match:
        output['up'] = int(up_match.group(1))
    new_match = re.search('\(new\)', line)
    if new_match:
        output['new'] = True

def read_skills(lines, output):
    skill_header_found = False
    skill_line = None
    for line in lines:
        if skill_header_found:
            skill_line = line
            break
        if line.find('スキル') >= 0:
            skill_header_found = True
    if not skill_line:
        return
    skills = []
    for skill in skill_line.split('」「'):
        skill = re.sub(".*「", '', skill)
        skill = re.sub("」.*", '', skill)
        lv_match = re.search('(.+)ＬＶ(\d+)(.*)', skill)
        oth_name_match = re.search('([^\(]+)', skill)
        sk_obj = {}
        if lv_match:
            sk_obj = {
                'name': translate(lv_match.group(1)),
                'level': int(lv_match.group(2))
            }
        elif oth_name_match:
            sk_obj = {'name': translate(oth_name_match.group(1))}
        else:
            sk_obj = {'name': translate(skill)}
        read_up_and_new(skill, sk_obj)
        skills.append(sk_obj)
    if len(skills):
        output['skills'] = skills

def read_titles(lines, output):
    title_header_found = False
    title_line = None
    for line in lines:
        if title_header_found:
            title_line = line
            break
        if line.find('称号') >= 0:
            title_header_found = True
    if not title_line:
        return
    titles = []
    for title in title_line.split('」「'):
        title = re.sub(".*「", '', title)
        title = re.sub("」.*", '', title)
        oth_name_match = re.search('([^\(]+)', title)
        if oth_name_match:
            t_obj = {'name': translate(oth_name_match.group(1))}
        else:
            t_obj = {'name': translate(title)}
        read_up_and_new(title, t_obj)
        titles.append(t_obj)
    if len(titles):
        output['titles'] = titles

def read_header(title, output):
    splits = re.split('　', title)
    output['kind'] = translate(splits[0])
    name = re.search('名前　(.+)', title)
    if name:
        name_str = re.sub('　', '', name.group(1))
        output['name'] = translate(name_str)

def parse(text):
    text = translate_numbers(text)
    # Remove beginning and end quotes.
    text = re.sub(".*『", '', text)
    text = re.sub("』.*", '', text).strip()

    # First line is the title, level and name
    lines = text.splitlines()

    output = {}

    # Sanity check: second line should say 'Statistics'
    STATISTICS = 'ステータス'
    if len(lines) > 1:
        lines[1].index(STATISTICS)

        # For weak appraisal, you can get a one-word summary like "Weak"
        headsplit = [x for x in re.split('　+', lines[1]) if len(x)]
        if headsplit[0] == STATISTICS and len(headsplit) > 1:
            output['stats_summary'] = translate(headsplit[1])

    if text.find('ステータスの鑑定に失敗しました') >= 0:
        output['failed_appraise'] = True

    # Read off attributes: HP, MP, SP_short, SP_long
    match_attrib_2(lines, 'ＨＰ：(\d+)／(\d+)（緑）', 'hp', output)
    match_attrib_2(lines, 'ＭＰ：(\d+)／(\d+)（青）', 'mp', output)
    match_attrib_2(lines, 'ＳＰ：(\d+)／(\d+)（黄）', 'sp_short', output)
    match_attrib_2(lines, '：(\d+)／(\d+)（赤）', 'sp_long', output)

    # Read off stats: offense, defense, mag. power, etc.
    match_attrib_1([lines[0]], 'ＬＶ(\d+)', 'level', output)
    match_attrib_1(lines, '平均攻撃能力：(\d+)', 'avg_offense', output)
    match_attrib_1(lines, '平均防御能力：(\d+)', 'avg_defense', output)
    match_attrib_1(lines, '平均魔法能力：(\d+)', 'avg_magic', output)
    match_attrib_1(lines, '平均抵抗能力：(\d+)', 'avg_resist', output)
    match_attrib_1(lines, '平均速度能力：(\d+)', 'avg_speed', output)
    match_attrib_1(lines, 'スキルポイント：(\d+)', 'skill_points', output)

    read_header(lines[0], output)
    read_skills(lines, output)
    read_titles(lines, output)

    return output


def print_stat(parsed, tag, color):
    """Print one of the stats (HP, MP, SPLong, SPShort)."""
    stat = ''
    stat += '%d/%d (%s)' % (parsed[tag], parsed[tag + '_max'], color)
    if (tag + '_plus') in parsed:
        stat += ' +%d' % parsed[tag + '_plus']
    if (tag + '_up') in parsed:
        stat += ' (%d up)' % parsed[tag + '_up']
    return stat

def print_attr(parsed, tag, name):
    """Print one of the attributes (offense, defense, etc)"""
    attr = ''
    attr += '%s: %d' % (name, parsed[tag])
    if (tag + '_plus') in parsed:
        attr += ' +%d' % parsed[tag + '_plus']
    if (tag + '_up') in parsed:
        attr += ' (%d up)' % parsed[tag + '_up']
    return attr

def print_skill_or_title(skill):
    sk_str = '[' + skill['name']
    if 'level' in skill:
        sk_str += ' (LV %d)' % skill['level']
    if 'up' in skill:
        sk_str += ' (%dup)' % skill['up']
    if 'new' in skill and skill['new']:
        sk_str += ' (new)'
    sk_str += ']'
    sk_str = sk_str.replace(' ', u'\xa0')  # non-breaking space
    sk_str = sk_str.replace('-', u'\u2011')  # (curse you, 3-D Maneuvering)
    return sk_str

def md_quote(out, times=1):
    if args.md:
        for i in range(times):
            out.write('> ')

def md_break(out):
    if args.md:
        out.write('  ')  # Write two spaces to force a line break.
    out.write('\n')

def stat_line(out, string):
    md_quote(out, 2)
    out.write(string)
    md_break(out)

def print_output(parsed, out):
    # Print header.
    md_quote(out)
    out.write(parsed['kind'])
    if 'level' in parsed:
        out.write(' ― LV %d' % parsed['level'])
    if 'name' in parsed:
        out.write(' ― %s' % parsed['name'])
    md_break(out)

    # Statistics: (Weak)?
    md_quote(out)
    out.write('Statistics:')
    if 'stats_summary' in parsed:
        out.write(' ' + parsed['stats_summary'])
    md_break(out)

    # Stats.
    if 'hp' in parsed:
        stat_line(out, 'HP: %s' % print_stat(parsed, 'hp', 'green'))
    if 'mp' in parsed:
        stat_line(out, 'MP: %s' % print_stat(parsed, 'mp', 'blue'))
    if 'sp_short' in parsed and 'sp_long' in parsed:
        stat_line(out, 'SP: %s, %s' % (
            print_stat(parsed, 'sp_short', 'yellow'),
            print_stat(parsed, 'sp_long', 'red')))
    if 'avg_offense' in parsed:
        stat_line(out, print_attr(parsed, 'avg_offense', 'Avg. Offense'))
    if 'avg_defense' in parsed:
        stat_line(out, print_attr(parsed, 'avg_defense', 'Avg. Defense'))
    if 'avg_magic' in parsed:
        stat_line(out, print_attr(parsed, 'avg_magic', 'Avg. Magic Power'))
    if 'avg_resist' in parsed:
        stat_line(out, print_attr(parsed, 'avg_resist', 'Avg. Resistance'))
    if 'avg_speed' in parsed:
        stat_line(out, print_attr(parsed, 'avg_speed', 'Avg. Speed'))

    # Skills.
    if 'skills' in parsed and len(parsed['skills']):
        md_quote(out)
        out.write('\n')
        md_quote(out)
        out.write('Skills:\n')
        skill_prints = []
        for skill in parsed['skills']:
            skill_prints.append(print_skill_or_title(skill))
        if args.split_skills:
            md_quote(out)
            out.write('\n')
            for skill in skill_prints:
                if args.md:
                    md_quote(out)
                    out.write('+ %s\n' % skill)
                else:
                    out.write('  • %s\n' % skill)
        else:
            md_quote(out, 2)
            out.write(u'\xa0• '.join(skill_prints))
            out.write('\n')

    # Skill Points.
    if 'skill_points' in parsed:
        md_quote(out)
        out.write('\n')
        md_quote(out)
        out.write('Skill points available: %s\n' %
                '{:,}'.format(parsed['skill_points']))

    # Titles.
    if 'titles' in parsed and len(parsed['titles']):
        md_quote(out)
        out.write('\n')
        md_quote(out)
        out.write('Titles:\n')
        title_prints = []
        for title in parsed['titles']:
            title_prints.append(print_skill_or_title(title))
        if args.split_titles:
            md_quote(out)
            out.write('\n')
            for title in title_prints:
                if args.md:
                    md_quote(out)
                    out.write('+ %s\n' % title)
                else:
                    out.write('  • %s\n' % title)
        else:
            md_quote(out, 2)
            out.write(' • '.join(title_prints))
            out.write('\n')

    # Failed appraise.
    if 'failed_appraise' in parsed and parsed['failed_appraise']:
        md_quote(out)
        out.write('Failed to appraise statistics.\n')

def process_file(in_fname, out_fname):
    with open(args.error_log, 'w+') as error_file:
        try:
            parsed = None
            with open(in_fname, 'r') as input_file:
                parsed = parse(input_file.read())
            print_output(parsed, sys.stdout)
            if not args.doprint and out_fname:
                with open(out_fname, 'w+') as output_file:
                    print_output(parsed, output_file)
            if args.update_dict:
                write_dictionary_file(dictionary, missing_words)
        except:
            traceback.print_exc(None, error_file)

# Main
process_file(args.input, args.output)
