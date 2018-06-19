import logging
log = logging.getLogger(__name__)

__author__ = 'Filinto Duran (duranto@gmail.com)'


class Range:
    """ defines a range object with start and end values. The End value is included in the return of get values.
        implements similar operations as set does

    """
    def __init__(self, start, end, step=1):
        if end < start:
            raise ValueError
        self.start = start
        self.end = end
        self.step = step

    @property
    def length(self):
        return int((self.end + 1 - self.start) / self.step)

    def copy(self):
        return Range(self.start, self.end, self.step)

    def overlaps(self, other):
        return (other.start <= self.end <= other.end) or (self.start <= other.end <= self.end)

    def contains(self, item):
        return self.__contains__(item)

    def __contains__(self, item):
        if isinstance(item, Range):
            return self.is_subrange(item)
        else:
            return self.start <= item <= self.end

    def is_contiguous_to(self, other):
        if not self.step == other.step:
            raise AttributeError('We have not implemented a function where ranges have different step')
        return (self.end + self.step) == other.start or (other.end + self.step) == self.start

    def __sub__(self, other):
        r = Range(self.start, self.end)
        return r.difference(other)

    def __add__(self, other):
        r = Range(self.start, self.end)
        return r.union(other)

    def __or__(self, other):
        """ overloading bitwise OR (|) """
        return self.union(other)

    def __and__(self, other):
        """ overloading bitwise AND (&) """
        return self.intersection(other)

    def __gt__(self, other):
        return self.start > other.start

    def __rshift__(self, other):
        """ defining shift as much bigger in the sense that this range is far to the right of the other

        """
        return self.start > other.end

    def __lshift__(self, other):
        """ defining left shift (<<) that this range is far to the left of the other that they don't have an union

        """
        return self.end < other.start

    def __lt__(self, other):
        """ less than (<) just check for start less than the other start """
        return self.start < other.start

    def __ge__(self, other):
        return self.start >= other.start

    def __le__(self, other):
        return self.start <= other.start

    def union(self, other, create_two_if_needed=False):
        if self.overlaps(other) or self.is_contiguous_to(other):
            return Range(min(self.start, other.start), max(self.end, other.end))
        if create_two_if_needed:
            return self.copy(), other.copy()
        raise ValueError

    def intersection(self, other):
        if self.overlaps(other):
            return Range(max(self.start, other.start), min(self.end, other.end))
        return None

    def _update(self, other, f1, f2):
        if self.overlaps(other) or self.is_contiguous_to(other):
            self.start = f1(self.start, other.start)
            self.end = f2(self.end, other.end)
            return self
        raise ValueError

    def union_update(self, other):
        """ mutable union

        """
        return self._update(other, min, max)

    def intersection_update(self, other):
        """ mutable intersection

        """
        return self._update(other, max, min)

    def is_subrange(self, other):
        return self.start >= other.start and self.end <= other.end

    def difference(self, other, split_if_needed=False):
        """ removes a range given by other from self

        """
        if not self.step == other.step:
            raise AttributeError('We have not implemented a function where ranges have different step')
        if not self.overlaps(other):    # no overlap return copy of self
            return self.copy()
        if self.is_subrange(other):     # complete coverage return none
            return None
        if other.end >= self.end:    # remove right piece
            return Range(self.start, other.start - self.step)
        if other.start <= self.start:  # remove left piece
            return Range(other.end + self.step, self.end)
        if split_if_needed:
            return Range(self.start, other.start - self.step), Range(other.end + self.step, self.end)
        raise ValueError("the flag split_if_needed was not set and the difference between "
                         "these two ranges would create two new ranges")

    def difference_update(self, other):
        """ mutable difference

        """
        if not self.step == other.step:
            raise AttributeError('We have not implemented a function where ranges have different step')

        if not self.overlaps(other):
            pass
        elif self.is_subrange(other):
            log.debug('Trying to remove a range that is bigger than self while updating is not possible')
            raise ValueError
        elif other.end >= self.end:    # remove right piece
            self.end = other.start - self.step
        elif other.start <= self.start:  # remove left piece
            self.start = other.end + self.step
        else:
            raise ValueError   # cannot update the range into two ranges
        return self

    def values(self):
        v = self.start
        while v <= self.end:
            yield v
            v += self.step

    def __iter__(self):
        return self.values()

    def __str__(self):
        return "{}-{}".format(self.start, self.end)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class TcpConnection:
    def __init__(self, server, server_port, client, client_port):
        self.server = server
        self.server_port = server_port
        self.client = client
        self.client_port = client_port

    def copy_reverse(self):
        return TcpConnection(self.client, self.client_port, self.server, self.server_port)

    def __eq__(self, other):
        return (self.server == other.server and self.server_port == other.server_port and
                self.client == other.client and self.client_port == other.client_port)

    def __str__(self):
        return '<Server: {}:{}  <-> Client: {}:{}'.format(self.server, self.server_port, self.client, self.client_port)
