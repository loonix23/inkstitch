from ..stitch_layer import StitchLayer
from ..utils import Category, Property, PropertyGridHelper, PropertyGridMixin, RandomizationMixin

from lib.i18n import _
from lib.stitch_plan import StitchGroup
from lib.stitches.running_stitch import running_stitch
from lib.svg import PIXELS_PER_MM


class RunningStitchLayer(StitchLayer, RandomizationMixin, PropertyGridMixin):
    @classmethod
    @property
    def DEFAULT_CONFIG(_class):
        return dict(
            name=_("Running Stitch"),
            stitch_length=2,
            tolerance=0.2,
            stitch_length_jitter_percent=0,
            repeats=1,
            repeat_stitches=True
        )

    @classmethod
    @property
    def LAYOUT(_class):
        return PropertyGridHelper(
            Category(_("Running Stitch")).children(
                Property("stitch_length", _("Stitch length asdfklafslj adfs kjlk ljasfd lkjasl kjfsda"),
                         help=_('Length of stitches. Stitches can be shorter according to the stitch tolerance setting.'),
                         min=0.1,
                         unit="mm",
                         ),
                Property("tolerance", _("Tolerance"),
                         help=_('All stitches must be within this distance from the path.  ' +
                                'A lower tolerance means stitches will be closer together.  ' +
                                'A higher tolerance means sharp corners may be rounded.'),
                         min=0.01,
                         unit="mm",
                         ),
            ),
            Category(_("Repeats")).children(
                Property(
                    "repeats", _("Repeats"),
                    help=_('Defines how many times to run down and back along the path.'),
                    min=1,
                ),
                Property(
                    "repeat_stitches", _("Repeat stitches"),
                    help=_('Should the exact same stitches be repeated in each pass?' +
                           'If not, different randomization settings are applied on each pass.'),
                ),
            )
        )

    uses_previous_stitch_group = False

    def num_copies(self):
        if self.config.repeat_stitches:
            # When repeating stitches, we use multiple copies of one pass of running stitch
            return 1
        else:
            # Otherwise, we re-run running stitch every time, so that
            # randomization is different every pass
            return self.config.repeats

    def running_stitch(self, path):
        stitches = []

        for i in range(self.num_copies()):
            if i % 2 == 0:
                this_path = path
            else:
                this_path = reversed(path)

            stitches.extend(running_stitch(
                this_path,
                self.config.stitch_length * PIXELS_PER_MM,
                self.config.tolerance * PIXELS_PER_MM,
                (self.config.stitch_length_jitter_percent > 0),
                self.config.stitch_length_jitter_percent,
                self.get_random_seed()
            ))

        if self.config.repeats > 0 and self.config.repeat_stitches:
            repeated_stitches = []
            for i in range(self.config.repeats):
                if i % 2 == 0:
                    repeated_stitches.extend(stitches)
                else:
                    # reverse every other pass
                    repeated_stitches.extend(reversed(stitches))
            stitches = repeated_stitches

        return StitchGroup(stitches=stitches, color=self.stroke_color)

    def to_stitch_groups(self):
        return [self.running_stitch(path) for path in self.paths]
