"""
===============================
Parallel Transport Tractography
===============================
Parallel Transport Tractography (PTT) :footcite:p:`Aydogan2021`

Let's start by importing the necessary modules.
"""

from dipy.core.gradients import gradient_table
from dipy.data import get_fnames, get_sphere
from dipy.direction import PTTDirectionGetter
from dipy.io.gradients import read_bvals_bvecs
from dipy.io.image import load_nifti, load_nifti_data
from dipy.io.stateful_tractogram import Space, StatefulTractogram
from dipy.io.streamline import save_trk
from dipy.reconst.csdeconv import ConstrainedSphericalDeconvModel, auto_response_ssst
from dipy.reconst.shm import CsaOdfModel
from dipy.tracking import utils
from dipy.tracking.local_tracking import LocalTracking
from dipy.tracking.stopping_criterion import ThresholdStoppingCriterion
from dipy.tracking.streamline import Streamlines
from dipy.viz import actor, colormap, has_fury, window

# Enables/disables interactive visualization
interactive = False

hardi_fname, hardi_bval_fname, hardi_bvec_fname = get_fnames(name="stanford_hardi")
label_fname = get_fnames(name="stanford_labels")

data, affine, hardi_img = load_nifti(hardi_fname, return_img=True)
labels = load_nifti_data(label_fname)
bvals, bvecs = read_bvals_bvecs(hardi_bval_fname, hardi_bvec_fname)
gtab = gradient_table(bvals, bvecs=bvecs)

seed_mask = labels == 2
white_matter = (labels == 1) | (labels == 2)
seeds = utils.seeds_from_mask(seed_mask, affine, density=1)

response, ratio = auto_response_ssst(gtab, data, roi_radii=10, fa_thr=0.7)
csd_model = ConstrainedSphericalDeconvModel(gtab, response, sh_order_max=6)
csd_fit = csd_model.fit(data, mask=white_matter)

###############################################################################
# We use the GFA of the CSA model to build a stopping criterion.

csa_model = CsaOdfModel(gtab, sh_order_max=6)
gfa = csa_model.fit(data, mask=white_matter).gfa
stopping_criterion = ThresholdStoppingCriterion(gfa, 0.25)

###############################################################################
# Prepare the PTT direction getter using the fiber ODF (FOD) obtain with CSD.
# Start the local tractography using PTT direction getter.

sphere = get_sphere(name="repulsion724")
fod = csd_fit.odf(sphere)
pmf = fod.clip(min=0)
ptt_dg = PTTDirectionGetter.from_pmf(pmf, max_angle=15, probe_length=0.5, sphere=sphere)

# Parallel Transport Tractography
streamline_generator = LocalTracking(
    direction_getter=ptt_dg,
    stopping_criterion=stopping_criterion,
    seeds=seeds,
    affine=affine,
    step_size=0.2,
)
streamlines = Streamlines(streamline_generator)
sft = StatefulTractogram(streamlines, hardi_img, Space.RASMM)
save_trk(sft, "tractogram_ptt_dg_pmf.trk")

if has_fury:
    scene = window.Scene()
    scene.add(actor.line(streamlines, colors=colormap.line_colors(streamlines)))
    window.record(scene=scene, out_path="tractogram_ptt_dg_pmf.png", size=(800, 800))
    if interactive:
        window.show(scene)

###############################################################################
# .. rst-class:: centered small fst-italic fw-semibold
#
# Corpus Callosum using ptt direction getter from PMF
#
#
#
# References
# ----------
#
# .. footbibliography::
#

###############################################################################
# .. include:: ../../links_names.inc
#
