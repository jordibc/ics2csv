#!/usr/bin/env python3

"""
Crea un fichero csv a partir de un icalendar, para los eventos
del Día Internacional de la Mujer y la Niña en la Ciencia
(11 de febrero).
"""

# For the csv specs: https://en.wikipedia.org/wiki/Comma-separated_values

import sys
import os
import argparse
from collections import OrderedDict
from datetime import datetime, timedelta


# Lo que queremos:
#   Título (sacado de la descripción)
#   Descripción
#   Fecha
#   Lugar
#   Enlace (sacado de la descripción)

important_fields = OrderedDict([
    ('TITLE', 'Título'),
    ('DESCRIPTION', 'Descripción'),
    ('DATE', 'Fecha'),
    ('LOCATION', 'Lugar'),
    ('LINK', 'Enlace')])



def main():
    parser = argparse.ArgumentParser(description=__doc__)
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

    with open(outfname, 'wt') as outfile:
        outfile.write(','.join(important_fields.values()) + '\n')
        for event in events:
            outfile.write(','.join('"%s"' % event.get(field, '')
                                   for field in important_fields.keys()) + '\n')

    print('The output is in file %s' % outfname)



def check_if_exists(fname):
    if os.path.exists(fname):
        answer = input('File %s already exists. Overwrite? [y/n] ' % fname)
        if not answer.lower().startswith('y'):
            sys.exit('Cancelling.')


def remove_malformed(events):
    bad_events = []
    for i, event in enumerate(events):
        if ('DESCRIPTION' not in event or
            not event['DESCRIPTION'].startswith('<a href=')):
            print('Event %d has bad DESCRIPTION. Skipping.' % (i + 1))
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
    titles = [event['TITLE'] for event in events]
    locations = [event['LOCATION'] for event in events]
    for i in range(len(events)):
        title, location = titles[i], locations[i]
        dups = [j for j in range(i + 1, len(events))
                if titles[j] == title and locations[j] == location]
        if dups:
            print('Warning: event %d seems to have duplicates: %s' %
                  (i + 1, ','.join('%d' % (j + 1) for j in dups)))


def read_icalendar(fname):
    "Create a list of events (dicts with fields) from an icalendar file"
    events = []
    event, field, text = {}, None, ''
    in_event = False
    for line in open(fname):
        if not in_event:
            if line.startswith('BEGIN:VEVENT'):
                in_event = True
        else:
            if line.startswith('END:VEVENT'):
                add_field(event, field, text)
                events.append(event)
                event, field, text = {}, None, ''
                in_event = False
            elif line.startswith(' '):
                text += line[1:].rstrip('\n')
            else:
                add_field(event, field, text)
                field, text = line.rstrip('\n').split(':', 1)
    return events


def add_field(event, field, text):
    "Add field to event, with the given text"
    if field is not None:
        for x, y in [('\\,', ','), ('"', '""'), ('\\n', '\n')]:
            text = text.replace(x, y)
        event[field] = text



if __name__ == '__main__':
    main()
