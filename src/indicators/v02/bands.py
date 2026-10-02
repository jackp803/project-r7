from decimal import Decimal


def population_bands(values,k):
    size=Decimal(len(values))
    middle=sum(values,Decimal(0))/size
    variance=sum(((value-middle)**2 for value in values),Decimal(0))/size
    stddev=variance.sqrt()
    return {'middle':middle,'stddev':stddev,'upper':middle+k*stddev,'lower':middle-k*stddev}


def donchian(values):
    upper=max(pair[0] for pair in values)
    lower=min(pair[1] for pair in values)
    return {'upper':upper,'lower':lower,'middle':(upper+lower)/Decimal(2)}
