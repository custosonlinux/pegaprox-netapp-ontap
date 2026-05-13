# NetApp® ONTAP® Snapshots — PegaProx Community Plugin

A [PegaProx](https://github.com/PegaProx/project-pegaprox) community plugin that adds VM-consistent NetApp® ONTAP® snapshot management directly to the PegaProx UI — for **NFS**, **iSCSI**, and **NVMe-oF** (NVMe/TCP, NVMe/FC) datastores.

> **Maturity levels:**
> - 🟡 **NFS** — Beta. Core workflows (snapshot, restore, clone, SnapMirror) are functional. Not yet production-hardened.
> - 🟡 **SAN — iSCSI** — Beta. Snapshot, single-VM restore, volume revert, and VM clone are fully implemented and end-to-end tested.
> - 🟡 **SAN — NVMe-oF** — Beta. Snapshot, single-VM restore, volume revert, and VM clone are fully implemented and end-to-end tested on NetApp ASA with NVMe/TCP. Not yet production-hardened.

---

## Feature Matrix

| Feature | NFS | iSCSI | NVMe-oF |
|---|:---:|:---:|:---:|
| Auto-Discovery | 🟡 Beta | 🟡 Beta | 🟡 Beta |
| VM-consistent Snapshots (crash / app / suspend) | 🟡 Beta | 🟡 Beta | 🟡 Beta |
| Scheduled Snapshots | 🟡 Beta | 🟡 Beta | 🟡 Beta |
| Email notifications per schedule | 🟡 Beta | 🟡 Beta | 🟡 Beta |
| snapmanifest (manifest rides inside ONTAP snapshot) | 🟡 Beta | 🟡 Beta | 🟡 Beta |
| Restore — SFSR (Single-File, NFS only) | 🟡 Beta | ❌ n/a | ❌ n/a |
| Restore — Single VM (LV-copy via temp clone) | ❌ n/a | 🟡 Beta | 🟡 Beta¹ |
| Restore — Volume Revert (all VMs) | ❌ n/a | 🟡 Beta | 🟡 Beta |
| VM Clone from snapshot | 🟡 Beta | 🟡 Beta | 🟡 Beta¹ |
| Clone from ONTAP-native snapshots | 🟡 Beta | 🟡 Beta | 🟡 Beta |
| Multi-VM snapshot | 🟡 Beta | 🟡 Beta | 🟡 Beta |
| ONTAP-native snapshot visibility | 🟡 Beta | 🟡 Beta | 🟡 Beta |
| SnapMirror® visibility & DR restore/clone | 🟡 Beta | 🔄 Planned | 🔄 Planned |
| Storage Provisioning (auto-setup) | ❌ n/a | 🟡 Beta | 🔄 Planned |
| Job cancellation | 🟡 Beta | 🟡 Beta | 🟡 Beta |

Legend: 🟡 Beta · 🔄 Planned · ❌ Not applicable

¹ NVMe Single VM Restore and Clone on ASA use a full volume clone via the ONTAP CLI bridge (`private/cli/volume/clone`). Direct namespace clone APIs are not available on ASA, but the volume clone approach achieves identical results (see platform table below).

---

## Platform & Protocol Compatibility

The plugin auto-detects the ONTAP platform (`san_optimized` flag) and adapts the available restore methods accordingly. No manual configuration is needed.

| Platform | Protocol | Snapshot | Single VM Restore | Volume Revert | Clone |
|---|---|:---:|:---:|:---:|:---:|
| FAS / AFF | NFS | ✅ | ✅ SFSR | — | ✅ FlexClone |
| FAS / AFF | iSCSI | ✅ | ✅ LUN clone | ✅ | ✅ LUN clone |
| FAS / AFF | NVMe-oF | ✅ | ✅ NS clone | ✅ | ✅ NS clone |
| ASA | iSCSI | ✅ | ✅ LUN clone | ✅ | ✅ LUN clone |
| ASA | NVMe-oF | ✅ | ✅ Volume clone² | ✅ | ✅ Volume clone² |

**How ASA NVMe single-VM restore/clone works:** Direct namespace clone APIs are not available on ASA (`POST protocols/nvme/namespaces` → 404, `POST storage/volumes` FlexClone → 405). The plugin uses the ONTAP CLI bridge (`POST private/cli/volume/clone`) to create a full volume clone from the snapshot instead. The NVMe namespace inside the clone volume inherits the parent subsystem mapping and becomes immediately visible on the Proxmox hosts as a new block device — exactly what is needed for the LVM `vgimportclone` + `dd` restore/clone flow.

² ASA NVMe uses `POST private/cli/volume/clone` (CLI bridge) instead of the native REST namespace clone. The restore/clone result is identical to iSCSI/FAS/AFF.

---

## Requirements

### PegaProx
Version **0.9.9** or later.

### ONTAP
All features are included in **ONTAP One** (ONTAP 9.10.1+) at no extra cost:

| Feature | License | Included in ONTAP One |
|---|---|---|
| Volume Snapshots | Base | ✓ |
| Single-File Snapshot Restore (SFSR) | SnapRestore® | ✓ |
| Volume Snapshot Restore (revert) | SnapRestore® | ✓ |
| FlexClone | FlexClone® | ✓ |
| NVMe-oF / iSCSI | SAN | ✓ |

**Tested platforms:** ONTAP 9.13+ (NFS), NetApp ASA (All-SAN Array) with NVMe/TCP — including single-VM restore and VM clone end-to-end (snapshot → clone → vgimportclone → dd → VM start).

### Proxmox packages (PVE nodes)

**For NFS** — no additional packages required.

**For iSCSI:**
```bash
apt install open-iscsi lvm2
```

**For NVMe-oF:**
```bash
apt install nvme-cli lvm2
# NVMe/TCP kernel module
modprobe nvme-tcp
```

### PegaProx host packages
`sshpass` (only needed for password-based SSH; not required with SSH key auth):
```bash
apt install sshpass    # Debian / Ubuntu
dnf install sshpass    # RHEL / Rocky
```

### Network access from the PegaProx host
```
PegaProx  →  Proxmox API         TCP 8006
PegaProx  →  ONTAP cluster-mgmt  TCP 443
PegaProx  →  Proxmox nodes       TCP 22 (SSH)
PegaProx  →  SMTP server         TCP 25/465/587  (optional, for email notifications)
```

---

## Installation

1. Copy the `netapp_ontap/` directory into your PegaProx `plugins/` folder.
2. Copy `config.example.json` to `config.json` and adjust if needed (defaults work out of the box).
3. In PegaProx: **Settings → Plugins → NetApp ONTAP Snapshots → Enable**.
4. Restart PegaProx or reload the plugin from the UI.

---

## Setup

### 1. ONTAP user

Create a dedicated ONTAP user with minimum required permissions:

```bash
# Create role
security login role create -role pegaprox-snap -cmddirname "volume snapshot"          -access all
security login role create -role pegaprox-snap -cmddirname "volume snapshot restore"   -access all
security login role create -role pegaprox-snap -cmddirname "volume snapshot restore-file" -access all
security login role create -role pegaprox-snap -cmddirname "storage/file/clone"        -access all

# Create user (HTTP + SSH password auth)
security login create -user-or-group-name pegaprox \
  -application http -authmethod password -role pegaprox-snap
```

### 2. Add ONTAP endpoint

In the plugin UI under **Settings → NetApp Systems → Add**:

| Field | Description |
|---|---|
| Name | Friendly label (e.g. `prod-cluster`) |
| Host | Cluster management LIF hostname or IP |
| Username / Password | ONTAP credentials |
| SSL Verify | Recommended: enabled |

### 3. Add Proxmox host

Under **Settings → Proxmox Hosts → Add** — add each Proxmox node or cluster that has datastores backed by ONTAP. Standalone nodes (not in a PVE cluster) are supported.

### 4. Run Auto-Discovery

Under **Settings → Discovery → Run** — the plugin scans your Proxmox hosts for NFS, iSCSI, and NVMe datastores and matches them to ONTAP volumes automatically.

You can also add volume mappings manually if auto-discovery cannot identify the correct mapping.

---

## SAN-specific setup (iSCSI / NVMe-oF)

### snapmanifest LV

SAN datastores (LVM-over-iSCSI or LVM-over-NVMe) do not have a filesystem that can hold manifest files. The plugin uses a small dedicated LV called **snapmanifest** that lives inside the same VG as your VM disks. It is formatted ext4 (64 MB by default) and rides inside every ONTAP snapshot automatically.

After discovery has found your SAN mapping, click **"Setup snapmanifest"** next to the mapping in the Settings tab. This creates and formats the LV. It is a one-time operation per VG.

### Restore methods (SAN)

Two restore methods are available for SAN datastores. The plugin selects the correct options automatically based on platform and protocol.

#### Single VM Restore (iSCSI / NVMe on FAS·AFF, iSCSI / NVMe on ASA)

Restores only the target VM's logical volumes without affecting other VMs on the same datastore:

1. The target VM is stopped.
2. A temporary clone is created from the snapshot on ONTAP (LUN clone for iSCSI; namespace clone for FAS/AFF NVMe; volume clone via CLI bridge for ASA NVMe).
3. The clone is mapped to the Proxmox host.
4. `vgimportclone` imports the clone's LVM VG under a temporary name.
5. Each disk LV of the target VM is copied (`dd bs=512M iflag=direct oflag=direct`) from the temporary VG to the live VG.
6. The temporary clone is unmapped and deleted from ONTAP.
7. The VM config is restored from the plugin database.
8. The VM is started.

Other VMs on the same datastore remain running throughout.

#### VM Clone (SAN)

Creates a new VM from a snapshot with a new VMID and freshly generated MAC addresses:

1. A temporary ONTAP clone is created from the snapshot.
2. `vgimportclone` imports the clone VG and reads the snapmanifest to discover disk layout.
3. New LVs are created in the live VG and the disks are copied via `dd`.
4. A new VM config is written with remapped disk references and regenerated MACs.
5. The temporary clone is cleaned up.

The VMID is reserved in PVE immediately before the disk copy begins to prevent ID conflicts during long-running operations.

#### Volume Revert (all SAN, including ASA NVMe)

Reverts the entire ONTAP volume to the snapshot state — affects **all VMs** on that datastore:

1. The target VM is stopped.
2. The LVM VG is deactivated on the Proxmox host (`vgchange -an`).
3. ONTAP reverts the entire volume to the snapshot state.
4. The VG is re-scanned and reactivated (`pvscan --cache && vgchange -ay`).
5. The VM config is restored from the plugin database.
6. The VM is started.

> ⚠️ **Volume Revert is destructive**: all data written to the volume *after* the snapshot is permanently lost. All VMs on the same SAN datastore are affected.

---

## Storage Provisioning (iSCSI)

The **Provisioning** tab automates the complete setup of a new iSCSI datastore — from ONTAP object creation to PVE storage registration — across all cluster nodes in a single operation.

### What is automated

1. **ONTAP side** — create (or reuse) a thin-provisioned SAN volume, a LUN, and an iGroup; add all selected host IQNs; map the LUN to the iGroup.
2. **Per PVE host** — iSCSI discovery (`iscsiadm -m discovery`), target login, multipath device detection (waits until `/dev/mapper/<WWID>` appears).
3. **First host** — `pvcreate`, `vgcreate` (linear or thin-provisioned LVM).
4. **All hosts** — `pvscan --cache -aay` to populate the LVM event cache so the VG activates on every node.
5. **PVE cluster** — `pvesm add lvm / lvmthin` (cluster-wide, run once).

### Remove datastore

The Provisioning tab also handles teardown: `pvesm remove`, VG deactivation and removal, iSCSI logout — and optionally deletes the ONTAP LUN and volume.

### Requirements

- `open-iscsi`, `multipath-tools`, `lvm2` installed on all PVE nodes (see package table below).
- A valid `/etc/multipath.conf` with NetApp settings (see template below).
- SSH access from PegaProx to all PVE nodes (configured under Settings → Proxmox Hosts).

> **NVMe-oF provisioning** is not yet automated. Use the manual steps below.

---

## SAN datastore — multi-host manual setup (NVMe-oF)

The steps below apply to **NVMe-oF** datastores. iSCSI datastores are set up automatically by the Provisioning tab (see above).

### Required packages (per PVE node)

| Protocol | Packages |
|---|---|
| iSCSI | `open-iscsi`, `multipath-tools`, `lvm2` |
| NVMe-oF | `nvme-cli`, `lvm2`; kernel module `nvme-tcp` |

Persist the NVMe/TCP kernel module across reboots:
```bash
echo nvme-tcp >> /etc/modules-load.d/nvme-tcp.conf
```

### multipath.conf — NetApp recommended settings

Required on every PVE node for both iSCSI and NVMe-oF. Add to `/etc/multipath.conf`:

```
defaults {
    find_multipaths    yes
    user_friendly_names yes
}
devices {
    device {
        vendor                "NETAPP"
        product               "LUN.*"
        path_grouping_policy  group_by_prio
        prio                  alua
        hardware_handler      "1 alua"
        failback              immediate
        path_checker          tur
        no_path_retry         queue
        features              "3 queue_if_no_path pg_init_retries 50"
        rr_weight             uniform
        rr_min_io_rq          1
    }
}
```

After writing: `systemctl restart multipathd`.

> **iSCSI**: the Provisioning tab handles `iscsiadm` discovery/login, `pvcreate`/`vgcreate`, `pvscan --cache -aay` activation on all nodes, and `pvesm` registration automatically. Manual steps are not needed for iSCSI.

### NVMe-oF — discovery.conf

NVMe/TCP connections are configured in `/etc/nvme/discovery.conf`, one entry per target/interface pair:

```
--transport=tcp --traddr=<target_ip> --host-iface=<nic> --host-traddr=<host_ip>
```

After editing, reconnect with `nvme connect-all`. The same LVM VG activation step (`pvscan --cache -aay`) applies for NVMe-backed LVM VGs on secondary hosts.

---

## Email notifications

Each schedule can send email notifications on snapshot job completion. Configure SMTP in **Settings → SMTP** first, then enable notifications per schedule:

| Option | Description |
|---|---|
| Enable notifications | Master toggle per schedule |
| Notify on | All events / Failures only / Success only |
| Recipients | Comma-separated email addresses |
| Send test email | Sends a test email using the current SMTP settings and the entered recipients |

Notifications include the schedule name, snapshot name, final status, and the last 30 log lines from the job.

---

## Job management

All snapshot, restore, and clone operations run as background jobs and are visible under **Jobs & History**.

- **Cancel**: Running jobs can be cancelled via the Cancel button. The job stops at the next safe checkpoint (between steps or between disk copies). Any partial work (temporary ONTAP clones, imported VGs, reserved VMIDs) is cleaned up automatically.
- **Delete**: Completed, failed, or cancelled jobs can be deleted individually or in bulk via "Cleanup".
- **Stale jobs**: If a job is stuck at "running" after a PegaProx restart (the job thread is gone but the DB entry was not updated), the Cancel button will detect the dead thread and immediately mark the job as cancelled.

---

## Troubleshooting

### Stale iSCSI clone LUN after a failed job

If a clone or restore job fails after the temporary ONTAP LUN has been mapped to the Proxmox host but before cleanup completes, the host may be left with a stale multipath device. Because the NetApp multipath configuration uses `no_path_retry queue`, any process that touches the lost device — including LVM (`vgs`, `pvs`) — will **hang indefinitely**.

**Symptoms:**
- `vgs`, `pvs`, or any LVM command hangs on the affected host
- `multipath -ll` shows a device with all paths in `failed faulty running` state
- The ONTAP volume still exists (visible in System Manager or CLI) but the LUN is no longer mapped

**Cleanup — run on every affected PVE host:**

1. **Identify the stale WWID:**
   ```bash
   multipath -ll | grep -B1 'failed faulty'
   # Note the WWID, e.g.: 3600a098038323449383f5a38746e4842
   ```

2. **Disable I/O queuing** — this unblocks any hanging LVM commands immediately:
   ```bash
   multipathd disablequeueing map 3600a098038323449383f5a38746e4842
   ```

3. **Flush the multipath device:**
   ```bash
   multipath -f 3600a098038323449383f5a38746e4842
   ```

4. **Remove the stale SCSI paths** (replace `sdl sdk sdm sdn` with the actual device names shown by `multipath -ll`):
   ```bash
   for d in sdl sdk sdm sdn; do
     echo 1 > /sys/block/$d/device/delete
   done
   ```

5. **Delete the temporary ONTAP clone volume** (`pgxclone_*`) via ONTAP System Manager or CLI:
   ```bash
   # ONTAP CLI:
   vol delete -vserver <svm> -volume pgxclone_<uuid> -foreground true
   ```

6. **Verify cleanup:**
   ```bash
   multipath -ll    # stale WWID must be gone
   vgs              # must return immediately without hanging
   ```

> **Why does this happen?** The `queue_if_no_path` feature in the NetApp multipath configuration keeps I/O queued in kernel memory when all paths to a LUN are lost — this prevents data loss during transient network outages but also means any process accessing the device blocks until paths return or the device is explicitly flushed. The plugin flushes stale devices automatically at the end of every job. This manual procedure is only needed if the automatic cleanup itself failed (e.g. due to an ONTAP API timeout or network error during the cleanup step).

---

## Performance — SAN disk copy

The `dd` copy used during Single VM Restore and VM Clone is tuned for NVMe storage and high-bandwidth networks:

```
dd if=<src_lv> of=<dst_lv> bs=512M iflag=direct oflag=direct conv=fsync
```

- **`bs=512M`** — large blocks minimize syscall overhead.
- **`iflag=direct oflag=direct`** — O_DIRECT on both sides bypasses the page cache and lets NVMe saturate the full device bandwidth without wasting RAM.
- **Timeout: 4 hours** — covers very large volumes even at constrained throughput.

---

## Configuration (`config.json`)

See `config.example.json` for all options:

| Key | Default | Description |
|---|---|---|
| `snapshot_prefix` | `"NPP_"` | Prefix added to all snapshot names |
| `default_consistency` | `"crash"` | Default consistency level (`crash`, `app`, `suspend`) |
| `default_restore_method` | `"sfsr"` | Default restore method (`sfsr`, `flexclone`, `san`) |
| `job_poll_interval_s` | `3` | How often to poll ONTAP job status (seconds) |
| `job_poll_timeout_s` | `300` | Max wait time for an ONTAP job (seconds) |
| `manifest_subdir` | `".netapp-snapmanifest"` | Directory inside the NFS mount for manifests |
| `flexclone_mount_base` | `"/mnt/pegaprox-clone"` | Temp mount point for FlexClone restores |

---

## Naming conventions

All internal names created by the plugin follow the patterns below. This makes it easy to identify plugin-owned objects on ONTAP and on Proxmox hosts, and to clean up manually if needed.

### ONTAP snapshot names

| Type | Pattern | Example |
|---|---|---|
| Manual snapshot | `{prefix}{user_input}` | `NPP_before_update` |
| Scheduled snapshot | `{prefix}{YYYYMMDD}_{HHMM}[_{schedule_name}]` | `NPP_20260507_1400_nightly` |

`prefix` defaults to `NPP_` and is configurable via `snapshot_prefix` in `config.json`.

### Temporary ONTAP objects (FlexClone volumes, LUNs, namespaces)

All temporary objects that the plugin creates on ONTAP during a clone or restore operation use the same prefix: **`pgxclone_`**. They are deleted automatically when the job completes (or fails).

| Object | Pattern | Example |
|---|---|---|
| NFS FlexClone volume | `pgxclone_{job_id[:8]}` | `pgxclone_ab12cd34` |
| NFS FlexClone junction path | `/{clone_name}` | `/pgxclone_ab12cd34` |
| iSCSI temporary LUN | `pgxclone_{job_id[:8]}` | `pgxclone_ab12cd34` |
| NVMe temporary namespace | `pgxclone_{job_id[:8]}` | `pgxclone_ab12cd34` |
| Full ONTAP LUN/NS path | `/vol/{volume_name}/{clone_name}` | `/vol/proxvol01/pgxclone_ab12cd34` |

The `pgxclone_` prefix (short, no hyphens, no special characters) was chosen because ONTAP LUN path components do not reliably allow hyphens on all platforms (notably ASA). Using the same prefix for NFS FlexClone volumes keeps the scheme consistent and predictable.

### Local temporary mount points on PVE nodes

These are local directories only — they never appear in ONTAP.

| Purpose | Pattern | Example |
|---|---|---|
| FlexClone NFS mount | `{flexclone_mount_base}/{clone_name}` | `/mnt/pegaprox-clone/pgxclone_ab12cd34` |
| DR restore NFS mount | `{flexclone_mount_base}/dr-{job_id[:8]}` | `/mnt/pegaprox-clone/dr-ab12cd34` |
| DR clone NFS mount | `{flexclone_mount_base}/dr-clone-{job_id[:8]}` | `/mnt/pegaprox-clone/dr-clone-ab12cd34` |

`flexclone_mount_base` defaults to `/mnt/pegaprox-clone`.

### SAN: LVM objects on Proxmox

| Object | Pattern | Example |
|---|---|---|
| snapmanifest LV | `netapp_snapmanifest` | fixed name, configurable via `snapmanifest_lv_name` |
| Temp mount point for snapmanifest write | `/tmp/.pgsi_{random[:10]}` | `/tmp/.pgsi_3f8a2c1b4e` |
| Imported temp VG (vgimportclone) | `{vg_name}` or `{vg_name}1` | `proxvg1` (suffix added by LVM if name collides) |

The temp VG name after `vgimportclone` is chosen by LVM automatically: it tries the base VG name and appends an incrementing number on collision.

### NFS manifest storage

| Object | Pattern | Example |
|---|---|---|
| Manifest directory | `{nfs_mount}/{manifest_subdir}/{snap_name}/` | `/mnt/nfs/.netapp-snapmanifest/NPP_20260507_1400/` |
| Manifest file | `…/manifest.json` | |
| VM config at snapshot time | `…/{vmid}.conf` | `…/100.conf` |

`manifest_subdir` defaults to `.netapp-snapmanifest`. Configurable in `config.json`.

### `manifest_path` prefixes (stored in DB)

The `manifest_path` column in `netapp_snapshots` uses a prefix to indicate where the manifest lives:

| Prefix | Meaning |
|---|---|
| *(plain file path)* | NFS — manifest is on the NFS datastore |
| `db:{snapshot_id}` | DB-only fallback (NFS write failed, or not applicable) |
| `snapmanifest:{vg}/{lv}/{snap_name}` | SAN — manifest is on the snapmanifest LV **and** in the DB |

### Default VM names for cloned VMs

When no name is provided by the user, the plugin generates a default:

| Clone type | Default name |
|---|---|
| NFS clone | `clone-{original_vm_name}` |
| SAN clone | `san-clone-{original_vm_name}` |
| DR clone | `dr-clone-{original_vm_name}` |

---

## Consistency levels

| Level | Behaviour |
|---|---|
| `crash` | Snapshot taken immediately — fastest, crash-consistent |
| `app` | QEMU Guest Agent `fsfreeze-freeze` before snapshot, `fsfreeze-thaw` after |
| `suspend` | VM suspended before snapshot, resumed after |

LXC containers: only `crash` is supported (no guest agent).

---

## Manifest

### NFS

Every plugin-managed NFS snapshot stores metadata inside the NFS datastore:

```
<nfs_mount_path>/.netapp-snapmanifest/<snap-name>/
  manifest.json    snapshot metadata + VM inventory
  100.conf         Proxmox config of VM 100 at snapshot time
  101.conf         …
```

### SAN (iSCSI / NVMe-oF)

The manifest is written to the **snapmanifest LV** (a dedicated 64 MB ext4 LV in the same VG) before each ONTAP snapshot is created. This ensures the manifest travels inside the snapshot and is available for restore:

```
/dev/{vg}/netapp_snapmanifest  (ext4, 64 MB)
  manifest.json
  vmconfigs/100.conf
  vmconfigs/101.conf
```

Additionally, the manifest is always stored in the plugin database as a fallback.

**ONTAP-native snapshots** (not created by the plugin) also contain the snapmanifest LV at the state it was in when the snapshot was taken (i.e. the last plugin-managed snapshot's manifest). The plugin reads this manifest during restore and clone to determine disk layout without relying on the current VM configuration.

---

## API reference

All routes are relative to `/api/plugins/netapp_ontap/api/`.

| Method | Path | Description |
|---|---|---|
| GET | `endpoints` | List ONTAP endpoints |
| POST | `endpoints/add` | Add endpoint |
| POST | `endpoints/delete` | Delete endpoint |
| POST | `endpoints/test` | Test connectivity |
| GET | `pve-hosts` | List Proxmox hosts |
| POST | `pve-hosts/add` | Add host |
| POST | `pve-hosts/delete` | Delete host |
| POST | `pve-hosts/test` | Test SSH connectivity |
| GET | `volume-mappings` | List volume mappings |
| POST | `volume-mappings/delete` | Delete a volume mapping |
| POST | `discover` | Run auto-discovery |
| GET | `snapshots` | List snapshots (last 200) |
| POST | `snapshots/create` | Create snapshot (async) |
| POST | `snapshots/delete` | Delete snapshot |
| GET | `snapshots/volumes` | List ONTAP volumes for an endpoint |
| GET | `snapshots/vms-for-mapping` | List VMs on a mapped datastore |
| GET | `snapshots/manifest` | Read snapshot manifest |
| POST | `san/snapmanifest-init` | Initialize snapmanifest LV on a SAN mapping |
| GET | `san/snapmanifest-check` | Check snapmanifest LV status |
| POST | `restore/start` | Start restore job (`method`: `sfsr` / `san_single` / `san` / `dr`) |
| GET | `restore/status` | Restore job status |
| POST | `clone/start` | Start clone job |
| POST | `clone/dr-start` | Start DR clone job |
| GET | `clone/nextid` | Suggest next free VMID |
| GET | `clone/nodes` | List available Proxmox nodes |
| GET | `schedules` | List schedules |
| POST | `schedules/add` | Create schedule |
| POST | `schedules/update` | Update schedule |
| POST | `schedules/delete` | Delete schedule |
| POST | `schedules/run-now` | Trigger schedule immediately |
| GET | `jobs/status` | List all jobs or single job (`?job_id=`) |
| POST | `jobs/cancel` | Cancel a running job |
| POST | `jobs/delete` | Delete a completed/failed/cancelled job |
| POST | `jobs/cleanup` | Delete all completed and failed jobs |
| GET | `snapmirror/relationships` | List SnapMirror relationships |
| POST | `snapmirror/scan` | Scan / refresh SnapMirror relationships |
| POST | `snapmirror/update` | Trigger a SnapMirror transfer |
| GET | `snapmirror/secondary-snapshots` | List snapshots on a secondary volume |
| POST | `snapmirror/ensure-export` | Ensure secondary volume is exported (NFS DR) |
| GET | `provisioning/datastores` | List provisioned datastores |
| POST | `provisioning/datastores` | Create datastore (starts provisioning job) |
| POST | `provisioning/datastores/remove` | Remove datastore (starts removal job) |
| POST | `provisioning/datastores/resize` | Resize datastore |
| POST | `provisioning/datastores/add-host` | Add a PVE host to an existing datastore |
| POST | `provisioning/datastores/remove-host` | Remove a PVE host from a datastore |
| GET | `provisioning/ontap-resources` | Browse volumes/LUNs/iGroups on an endpoint (wizard) |
| GET | `provisioning/pve-hosts` | List configured PVE hosts (wizard) |
| GET | `settings/smtp` | Load SMTP configuration |
| POST | `settings/smtp/save` | Save SMTP configuration |
| POST | `settings/smtp/test` | Test SMTP connection |
| POST | `settings/notify-test` | Send a test notification email |
| GET | `ui` | Plugin management UI |

---

## License

GNU Affero General Public License v3.0 (AGPLv3) — see [LICENSE](LICENSE).

Copyright (c) 2026 Birger Peer Küpper

---

## Trademarks

NetApp, ONTAP, SnapMirror, SnapVault, SnapRestore, and FlexClone are registered trademarks of NetApp, Inc. in the United States and/or other countries. All other trademarks are the property of their respective owners.

This project is an independent community plugin and is not affiliated with, endorsed by, or sponsored by NetApp, Inc.
