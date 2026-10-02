"""Persist actual monotonic observation intervals; fixture clocks stay separate."""
from datetime import datetime
from math import ceil


def initial_forward_observation():
    return dict(started_at=None,observed_at=None,last_monotonic_ns=None,process_instance=None,
        real_elapsed_ns=0,real_healthy_ns=0,simulated_elapsed_seconds=0,simulated_healthy_seconds=0,
        max_observed_gap_seconds=0,observations=0,last_healthy=False,clock_status='NOT_OBSERVED')


def record_forward_observation(runtime, service, now, healthy):
    row=runtime['forward']; at=now.isoformat().replace('+00:00','Z')
    mono=service.monotonic_clock()
    if type(mono) is not int or mono<0: raise ValueError('Actual nonnegative monotonic nanoseconds required')
    if row['started_at'] is None: row['started_at']=at
    row['clock_status']='CONSISTENT'
    if row['observed_at'] is not None:
        prior=datetime.fromisoformat(row['observed_at'].replace('Z','+00:00'))
        wall=(now-prior).total_seconds()
        same_process=row['process_instance']==service._instance_id
        measured=mono-row['last_monotonic_ns'] if same_process else 0
        gap=max(wall,measured/1_000_000_000)
        row['max_observed_gap_seconds']=max(row['max_observed_gap_seconds'],max(0,ceil(gap)))
        if wall<0 or measured<0:
            row['clock_status']='CLOCK_REGRESSION'; healthy=False
        elif runtime['mode']=='ACCELERATED_FIXTURE':
            row['simulated_elapsed_seconds']+=int(wall)
            if healthy and row['last_healthy'] and gap<=service.promotion.as_dict()['maximum_observation_gap_seconds']:
                row['simulated_healthy_seconds']+=int(wall)
        elif same_process:
            # Wall jumps never create elapsed credit. Monotonic time supplies
            # credit, and a >2s discrepancy makes this entire interval invalid.
            if abs(wall-measured/1_000_000_000)>2:
                row['clock_status']='WALL_MONOTONIC_DIVERGED'; healthy=False
            else:
                row['real_elapsed_ns']+=measured
                if healthy and row['last_healthy'] and gap<=service.promotion.as_dict()['maximum_observation_gap_seconds']:
                    row['real_healthy_ns']+=measured
    row.update(observed_at=at,last_monotonic_ns=mono,process_instance=service._instance_id,
               last_healthy=healthy,observations=row['observations']+1)
