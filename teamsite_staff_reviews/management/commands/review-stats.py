import re
from collections import Counter
from typing import Iterable

import tablib
from django.core.management import BaseCommand
from reviews.models import ReviewFormResponse, ReviewPeriod
from teamsite.models import ChangeLogEntry

pattern = re.compile(r"\s+", flags=re.MULTILINE)

stopwords = """
i
me
my
myself
we
our
ours
ourselves
you
your
yours
yourself
yourselves
he
him
his
himself
she
her
hers
herself
it
its
itself
they
them
their
theirs
themselves
what
which
who
whom
this
that
these
those
am
is
are
was
were
be
been
being
have
has
had
having
do
does
did
doing
a
an
the
and
but
if
or
because
as
until
while
of
at
by
for
with
about
against
between
into
through
during
before
after
above
below
to
from
up
down
in
out
on
off
over
under
again
further
then
once
here
there
when
where
why
how
all
any
both
each
few
more
most
other
some
such
no
nor
not
only
own
same
so
than
too
very
s
t
can
will
just
don
should
now
ive
im
eg
us
also
""".split(
    "\n"
)
stopwords = [s.strip() for s in stopwords]


def count_words(value):
    value = pattern.split(value)
    value = [v for v in value if len(v.strip()) > 0]
    return len(value)


class Command(BaseCommand):
    help = """
    Calculate stats for review process
    """

    def handle(self, *args, **options):
        all_text = []
        for res in ReviewFormResponse.objects.all():
            words = res.value.lower()
            words = "".join([l for l in words if l.isalpha() or l == " "])
            words = pattern.split(words)
            words = [v.strip() for v in words]
            if "sf" in words:
                words.remove("sf")
                words += ["social", "finance"]
            words = [v for v in words if len(v) > 0 and v not in stopwords]
            all_text.extend(words)

        for ix, word in enumerate(all_text):
            if all_text[ix].endswith("s"):
                all_text[ix] = word[:-1]
            if all_text[ix].endswith("ing"):
                all_text[ix] = word[:-3]

        ctr = Counter(all_text).most_common(100)
        for c in ctr:
            print(f"{c[0]},{c[1]}")

    def changes_by_time(self):
        entries: Iterable(ChangeLogEntry) = ChangeLogEntry.objects.for_type(
            ReviewFormResponse
        ).order_by("modified_time")

        char_length = word_length = 0
        reviewers = set()
        cohorts = []

        timeseries = []

        for e in entries:
            value = e.model_object.value
            prev_value = e.previous.model_object.value if e.previous else ""
            char_length = char_length + len(value) - len(prev_value)
            word_length = word_length + count_words(value) - count_words(prev_value)

            if e.change_type == ChangeLogEntry.ChangeType.CREATE:
                nomination = e.model_object.nomination
                name = nomination.reviewer_name
                if name not in reviewers:
                    cohorts.append(
                        nomination.reviewer.profile.cohort
                        if nomination.reviewer
                        else "External"
                    )

                reviewers.add(name)

            datapoint = {
                "time": e.modified_time,
                "char_length": char_length,
                "word_length": word_length,
                "reviewers": len(reviewers),
            }

            for key, count in Counter(cohorts).items():
                datapoint[key] = count

            timeseries.append(datapoint)

        last_datapoint = timeseries[-1]
        columns = list(last_datapoint.keys())

        timeseries = [[t.get(k) for k in columns] for t in timeseries]

        data = tablib.Dataset(title="Reviews")
        data.headers = last_datapoint.keys()
        data.extend(timeseries)

        with open("review-stats.xlsx", "wb") as FILE:
            FILE.write(data.export("xlsx"))
