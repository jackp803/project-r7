"""Wilder average seeded from exactly n observed differences/ranges."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class WilderAverage:
    window: int
    count: int=0
    total: Decimal=Decimal('0')
    value: Decimal | None=None

    def push(self,value):
        self.count+=1
        if self.value is None:
            self.total+=value
            if self.count==self.window: self.value=self.total/Decimal(self.window)
        else:
            self.value=(self.value*Decimal(self.window-1)+value)/Decimal(self.window)
        return self.value
