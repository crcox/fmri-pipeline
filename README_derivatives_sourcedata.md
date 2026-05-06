fmriprep creates some symbolic links in derivatives/sourcedata/freesurfer to surfaces that exist within the container but then cannot be referenced after fmriprep ends.

rsync: [generator] symlink "/mnt/relearn-nas-1/Research/crcox/MRI/semantic-multitask/York/derivatives/sourcedata/freesurfer/sub-001/surf/lh.fsaverage.sphere.reg" -> "lh.sphere.reg" failed: No data available (61)
rsync: [generator] symlink "/mnt/relearn-nas-1/Research/crcox/MRI/semantic-multitask/York/derivatives/sourcedata/freesurfer/sub-001/surf/lh.pial" -> "lh.pial.T1" failed: No data available (61)
rsync: [generator] symlink "/mnt/relearn-nas-1/Research/crcox/MRI/semantic-multitask/York/derivatives/sourcedata/freesurfer/sub-001/surf/lh.white.H" -> "lh.white.preaparc.H" failed: No data available (61)
rsync: [generator] symlink "/mnt/relearn-nas-1/Research/crcox/MRI/semantic-multitask/York/derivatives/sourcedata/freesurfer/sub-001/surf/lh.white.K" -> "lh.white.preaparc.K" failed: No data available (61)
rsync: [generator] symlink "/mnt/relearn-nas-1/Research/crcox/MRI/semantic-multitask/York/derivatives/sourcedata/freesurfer/sub-001/surf/rh.fsaverage.sphere.reg" -> "rh.sphere.reg" failed: No data available (61)
rsync: [generator] symlink "/mnt/relearn-nas-1/Research/crcox/MRI/semantic-multitask/York/derivatives/sourcedata/freesurfer/sub-001/surf/rh.pial" -> "rh.pial.T1" failed: No data available (61)
rsync: [generator] symlink "/mnt/relearn-nas-1/Research/crcox/MRI/semantic-multitask/York/derivatives/sourcedata/freesurfer/sub-001/surf/rh.white.H" -> "rh.white.preaparc.H" failed: No data available (61)
rsync: [generator] symlink "/mnt/relearn-nas-1/Research/crcox/MRI/semantic-multitask/York/derivatives/sourcedata/freesurfer/sub-001/surf/rh.white.K" -> "rh.white.preaparc.K" failed: No data available (61)
rsync error: some files/attrs were not transferred (see previous errors) (code 23) at main.c(1327) [sender=3.2.5]
