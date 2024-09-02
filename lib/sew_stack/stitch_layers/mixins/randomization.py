import os
from secrets import randbelow

import wx.propgrid

from ..stitch_layer_editor import Category, Property
from ....i18n import _
from ....utils import get_resource_dir, prng

editor_instance = None


class RandomSeedEditor(wx.propgrid.PGTextCtrlAndButtonEditor):
    def CreateControls(self, property_grid, property, position, size):
        if wx.SystemSettings().GetAppearance().IsDark():
            randomize_icon_file = 'randomize_20x20_dark.png'
        else:
            randomize_icon_file = 'randomize_20x20.png'
        randomize_icon = wx.Image(os.path.join(get_resource_dir("icons"), randomize_icon_file)).ConvertToBitmap()
        # button = wx.Button(property_grid, wx.ID_ANY, _("Re-roll"))
        # button.SetBitmap(randomize_icon)

        window_list = super().CreateControls(property_grid, property, position, size)
        button = window_list.GetSecondary()
        button.SetBitmap(randomize_icon)
        button.SetLabel("")
        button.SetToolTip(_("Re-roll"))
        return window_list


class RandomSeedProperty(wx.propgrid.IntProperty):
    def DoGetEditorClass(self):
        return wx.propgrid.PropertyGridInterface.GetEditorByName("RandomSeedEditor")

    def OnEvent(self, propgrid, primaryEditor, event):
        if event.GetEventType() == wx.wxEVT_COMMAND_BUTTON_CLICKED:
            self.SetValue(randbelow(int(1e8)))
            return True
        return False


class RandomizationPropertiesMixin:
    @classmethod
    def randomization_properties(cls):
        # We have to register the editor class once. We have to save a reference
        # to the editor to avoid letting it get garbage collected.
        global editor_instance
        if editor_instance is None:
            editor_instance = RandomSeedEditor()
            wx.propgrid.PropertyGrid.DoRegisterEditorClass(editor_instance, "RandomSeedEditor")

        return Category(_("Randomization")).children(
            Property("random_seed", _("Random seed"), type=RandomSeedProperty,
                     # Wow, it's really hard to explain the concept of a random seed to non-programmers...
                     help=_("The random seed is used when handling randomization settings.  " +
                            "Click the button to choose a new random seed, which will generate random features differently. " +
                            "Alternatively, you can enter your own random seed.  If you reuse a random seed, random features " +
                            "will look the same.")),
            Property("stitch_jitter", _("Jitter stitches"), unit="mm", prefix="±",
                     help=_("Move stitches randomly by up to this many millimeters."))
        )


class RandomizationMixin:
    def get_random_seed(self):
        if 'random_seed' not in self.config:
            self.config.random_seed = self.element.get_default_random_seed() or ""

        return self.config.random_seed

    def jitter_stitches(self, stitches):
        """Randomly move stitches by modifying a list of stitches in-place."""

        if 'stitch_jitter' in self.config and self.config.stitch_jitter:
            rand_iter = iter(prng.iter_uniform_floats(self.get_random_seed(), "stitch_jitter"))

            for stitch in stitches:
                stitch.x += next(rand_iter) * 2 * self.config.stitch_jitter - self.config.stitch_jitter
                stitch.y += next(rand_iter) * 2 * self.config.stitch_jitter - self.config.stitch_jitter
