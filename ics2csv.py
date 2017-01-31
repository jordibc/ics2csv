#!/usr/bin/env python3

"""
Crea un fichero csv a partir de un icalendar, para los eventos del
Día Internacional de la Mujer y la Niña en la Ciencia (11 de febrero).

En el fichero están los siguientes campos:
* Título (sacado de la descripción)
* Descripción (modificada, sin título ni enlace)
* Fecha
* Lugar
* Enlace (sacado de la descripción)
"""

# For the csv specs: https://en.wikipedia.org/wiki/Comma-separated_values

import sys
import os
from argparse import ArgumentParser, RawDescriptionHelpFormatter as fmt
from datetime import datetime, timedelta


def main():
    parser = ArgumentParser(description=__doc__, formatter_class=fmt)
    parser.add_argument('file', metavar='FILE', help='icalendar file')
    parser.add_argument('--output', '-o', help='output file')
    parser.add_argument('--overwrite', action='store_true',
                        help='do not check if output file exists')
    parser.add_argument('--no-warn-duplicates', action='store_true',
                        help='do not warn about possible duplicates')
    args = parser.parse_args()

    events = read_icalendar(args.file)
    remove_malformed(events)
    extract_fields(events)
    if not args.no_warn_duplicates:
        check_duplicates(events)

    outfname = args.output or '%s.csv' % args.file
    if not args.overwrite:
        check_if_exists(outfname)

    write_fields_csv(events, outfname)


def write_fields_csv(events, fname):
    "Write in file fname some of the events fields, as comma-separated values"
    fields, names = zip(*[('TITLE',       'Título'),
                          ('DESCRIPTION', 'Descripción'),
                          ('DATE',        'Fecha'),
                          ('LOCATION',    'Lugar'),
                          ('LINK',        'Enlace')])
    get = lambda event, field: event.get(field, '').replace('"', '""')
    with open(fname, mode='wt', encoding='utf8') as out:
        write = lambda xs: out.write(','.join('"%s"' % x for x in xs) + '\n')
        write(names)
        for event in events:
            write(get(event, field) for field in fields)
    print('The output is in file %s' % fname)


def check_if_exists(fname):
    if os.path.exists(fname):
        answer = input('File %s already exists. Overwrite? [y/n] ' % fname)
        if not answer.lower().startswith('y'):
            sys.exit('Cancelling.')


def remove_malformed(events):
    bad_events = []
    for i, event in enumerate(events):
        if 'DESCRIPTION' not in event:
            print('Event %d has no DESCRIPTION. Skipping:' % (i + 1))
            bad_events.append(i)
        elif not event['DESCRIPTION'].startswith('<a href='):
            print('Event %d has bad DESCRIPTION. Skipping:' % (i + 1))
            print('  %s...' % repr(event['DESCRIPTION'][:70]))
            bad_events.append(i)
    for i in bad_events[::-1]:
        events.pop(i)


def extract_fields(events):
    for event in events:
        extract_title_and_link(event)
        extract_date(event)


def extract_title_and_link(event):
    "Create fields 'TITLE' and 'LINK', and update 'DESCRIPTION'"
    # event['DESCRIPTION'] is expected to look like:
    # '<a href="[link]">[title]</a>[description]'
    desc = event['DESCRIPTION']
    link_start = desc.find('href=') + 5
    link_end = desc.find('>')
    text_end = desc.find('</a>')
    event['TITLE'] = desc[link_end+1:text_end].strip()
    event['LINK'] = desc[link_start:link_end].strip('"')
    event['DESCRIPTION'] = desc[text_end+4:].strip()


def extract_date(event):
    "Create field 'DATE' with its correct readable form"
    if 'DTSTART;VALUE=DATE' in event:
        date = event['DTSTART;VALUE=DATE']
        event['DATE'] = '%s/%s/%s' % (date[6:8], date[4:6], date[:4])
    elif 'DTSTART;TZID=Europe/Madrid' in event:
        date = datetime.strptime(event['DTSTART;TZID=Europe/Madrid'],
                                 '%Y%m%dT%H%M%S')
        event['DATE'] = date.strftime('%d/%m/%Y %H:%M')
    elif 'DTSTART' in event:
        date = datetime.strptime(event['DTSTART'],
                                 '%Y%m%dT%H%M%SZ') + timedelta(hours=1)
        event['DATE'] = date.strftime('%d/%m/%Y %H:%M')
    else:
        raise RuntimeError('Missing date in event: %s' % event)


def check_duplicates(events):
    "Warn about possible duplicates in events, if any seen"
    seen = {}
    for i, event in enumerate(events):
        identifier = (event['TITLE'], event['LOCATION'])
        if identifier in seen:
            print('Warning: event %d seems to be a duplicate of %d' %
                  (i + 1, seen[identifier] + 1))
        else:
            seen[identifier] = i


def read_icalendar(fname):
    "Create a list of events (dicts with fields) from an icalendar file"
    events = []
    event, field, text = {}, None, ''
    in_event = False
    sublevel = 0
    for line in open(fname, encoding='utf8'):
        if not in_event:
            if line.startswith('BEGIN:VEVENT'):
                in_event = True
        else:
            if line.startswith('END:VEVENT'):
                add_field(event, field, text)
                events.append(event)
                event, field, text = {}, None, ''
                in_event = False
            elif line.startswith('BEGIN:'):
                add_field(event, field, text)
                sublevel += 1
            elif line.startswith('END:'):
                sublevel -= 1
            elif sublevel == 0:
                if line.startswith(' '):
                    text += line[1:].rstrip('\n')
                else:
                    add_field(event, field, text)
                    field, text = line.rstrip('\n').split(':', 1)
    return events


def add_field(event, field, text):
    "Add field to event, with the given text"
    if field is not None:
        event[field] = text.replace('\\,', ',').replace('\\n', '\n')



if __name__ == '__main__':
    main()
