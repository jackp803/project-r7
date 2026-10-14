This checkpoint covers the six sealed FIXTURE recovery/market cases and private
backup restoration only. It does not qualify ordinary Paper or the full PQR.

Executable revision: `525abcb09e62538476e676a2dce26c91830c5772`.
The local Windows package is under the approved project root:
`artifacts/paper-mapping-takeover-20261013-9b2fb655/build-525abcb/dist/R7/R7.exe`.

The actual formal entrypoints exercised were:

```powershell
& $executable init-profile --config $fixtureConfig --data-root $fixtureData --cloud-root $syntheticCloud --execution-mode FIXTURE --instance-id $fixtureInstance --port $loopbackPort
& $executable prepare-fixture --config $fixtureConfig --scenario positive --paper-case hold-for-recovery
& $executable configure-research --config $fixtureConfig --selection-profile $researchSelection
& $executable enroll-owner --config $fixtureConfig --username native-fixture-owner
& $executable serve --config $fixtureConfig
& $executable research-worker --config $fixtureConfig --once
& $executable configure-paper --config $fixtureConfig --selection-profile $paperSelection
& $executable paper-worker --config $fixtureConfig --maximum-ticks 2
& $executable stop-product --config $fixtureConfig --role runtime
& $executable stop-product --config $fixtureConfig --role control
& $executable backup-product-data --config $fixtureConfig --destination $privateBackup
& $executable verify-product-backup --config $fixtureConfig --destination $privateBackup
& $executable restore-product-data --config $fixtureConfig --backup $privateBackup --destination $restoredRoot
```

The variables represent fresh disjoint private FIXTURE paths, an available
loopback port and the installed executable. They are not ordinary financial
settings. Enrollment uses the existing interactive local CLI; passwords are not
retained in this evidence. Authentication, scan/enqueue and PaperStart/pause
used the actual guarded loopback product API. No database rows were hand-edited.
Configure-paper was executed after stopping Control, then Control was restarted.
Managed stop and forced termination were observed separately.

The six actual cases passed: hold-for-recovery, protection-rejected-hold,
partial-fill-hold, duplicate-market-hold, missing-market-hold and
stale-market-hold. Each closed its original position with the actual canonical
two-fill/one-trade graph. Both protected/partial backup copies preserved original
truth, remained RESTORED_INHIBITED/DISCONNECTED and rejected the native worker.

Remaining PQR-05 work includes standing-protection missing/stale/lost observations,
research timeout/resource faults while protection runs, actual host capacity and
stale generation operation fencing. Complete current-source and PQR-02/03/04/06/07
qualification, ordinary positive admission and unattended operation remain pending.
Ubuntu24.04/26.04 and real cloud/dataset/forward commissioning have no new evidence.
Provider requests, real credentials, capital and GitHub compute remained zero/none.
