import datetime

def ticstime(gametics):
    ms = ((gametics % 35) / 35) * 100
    secs = gametics / 35
    mins = secs / 60
    hours = mins / 60
    secs = secs % 60

    if hours >= 1:
        mins = mins % 60
        return '%d:%02d:%02d.%02d' % (hours, mins, secs, ms)
    else:
        return '%d:%02d.%02d' % (mins, secs, ms)

COLOUR_CHAR = '\034'
def strip_colours(name):
    out = ''

    iscol = False
    isbracket = False

    for i in range(len(name)):
        c = name[i]

        if iscol:
            if c == '[':
                isbracket = True
            elif c == ']':
                isbracket = False

            if not isbracket:
                iscol = False

            continue
        elif c == COLOUR_CHAR:
                iscol = True
                continue

        out = out + c

    return out

def format_date(date):
    dt = datetime.datetime.strptime(date, '%Y%m%d')
    return dt.strftime('%d %B %Y')

def format_timestamp(ts):
    dt = datetime.datetime.utcfromtimestamp(ts)
    return dt.strftime('%d %B %Y')
