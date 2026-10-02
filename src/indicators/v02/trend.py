"""Declared EMA seed; bounded state rather than retained full histories."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class EMA:
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
            alpha=Decimal(2)/Decimal(self.window+1)
            self.value=alpha*value+(Decimal(1)-alpha)*self.value
        return self.value
