# Authors: see git history
#
# Copyright (c) 2010 Authors
# Licensed under the GNU GPL version 3.0 or later.  See the file LICENSE for details.

from .about import About
from .apply_palette import ApplyPalette
from .apply_threadlist import ApplyThreadlist
from .auto_run import AutoRun
from .auto_satin import AutoSatin
from .break_apart import BreakApart
from .cleanup import Cleanup
from .commands_scale_symbols import CommandsScaleSymbols
from .convert_to_satin import ConvertToSatin
from .convert_to_stroke import ConvertToStroke
from .cut_satin import CutSatin
from .cutwork_segmentation import CutworkSegmentation
from .density_map import DensityMap
from .display_stacking_order import DisplayStackingOrder
from .duplicate_params import DuplicateParams
from .element_info import ElementInfo
from .fill_to_stroke import FillToStroke
from .flip import Flip
from .generate_palette import GeneratePalette
from .global_commands import GlobalCommands
from .gradient_blocks import GradientBlocks
from .input import Input
from .install import Install
from .install_custom_palette import InstallCustomPalette
from .jump_to_stroke import JumpToStroke
from .jump_to_trim import JumpToTrim
from .layer_commands import LayerCommands
from .lettering import Lettering
from .lettering_along_path import LetteringAlongPath
from .lettering_custom_font_dir import LetteringCustomFontDir
from .lettering_font_sample import LetteringFontSample
from .lettering_force_lock_stitches import LetteringForceLockStitches
from .lettering_generate_json import LetteringGenerateJson
from .lettering_edit_json import LetteringEditJson
from .lettering_remove_kerning import LetteringRemoveKerning
from .lettering_set_color_sort_index import LetteringSetColorSortIndex
from .letters_to_font import LettersToFont
from .object_commands import ObjectCommands
from .object_commands_toggle_visibility import ObjectCommandsToggleVisibility
from .outline import Outline
from .output import Output
from .palette_split_text import PaletteSplitText
from .palette_to_text import PaletteToText
from .params import Params
from .png_realistic import PngRealistic
from .png_simple import PngSimple
from .preferences import Preferences
from .print_pdf import Print
from .redwork import Redwork
from .remove_duplicated_points import RemoveDuplicatedPoints
from .remove_embroidery_settings import RemoveEmbroiderySettings
from .reorder import Reorder
from .satin_multicolor import SatinMulticolor
from .select_elements import SelectElements
from .selection_to_guide_line import SelectionToGuideLine
from .selection_to_pattern import SelectionToPattern
from .sew_stack_editor import SewStackEditor
from .simulator import Simulator
from .stitch_plan_preview import StitchPlanPreview
from .stitch_plan_preview_undo import StitchPlanPreviewUndo
from .stroke_to_lpe_satin import StrokeToLpeSatin
from .tartan import Tartan
from .test_swatches import TestSwatches
from .thread_list import ThreadList
from .troubleshoot import Troubleshoot
from .unlink_clone import UnlinkClone
from .update_svg import UpdateSvg
from .zigzag_line_to_satin import ZigzagLineToSatin
from .zip import Zip

__all__ = extensions = [About,
                        ApplyPalette,
                        ApplyThreadlist,
                        AutoRun,
                        AutoSatin,
                        BreakApart,
                        Cleanup,
                        CommandsScaleSymbols,
                        ConvertToSatin,
                        ConvertToStroke,
                        CutSatin,
                        CutworkSegmentation,
                        DensityMap,
                        DisplayStackingOrder,
                        DuplicateParams,
                        ElementInfo,
                        FillToStroke,
                        Flip,
                        GeneratePalette,
                        GlobalCommands,
                        GradientBlocks,
                        Input,
                        Install,
                        InstallCustomPalette,
                        JumpToStroke,
                        JumpToTrim,
                        LayerCommands,
                        Lettering,
                        LetteringAlongPath,
                        LetteringCustomFontDir,
                        LetteringEditJson,
                        LetteringFontSample,
                        LetteringForceLockStitches,
                        LetteringGenerateJson,
                        LetteringRemoveKerning,
                        LetteringSetColorSortIndex,
                        LettersToFont,
                        ObjectCommands,
                        ObjectCommandsToggleVisibility,
                        Outline,
                        Output,
                        PaletteSplitText,
                        PaletteToText,
                        Params,
                        PngRealistic,
                        PngSimple,
                        Preferences,
                        Print,
                        Redwork,
                        RemoveDuplicatedPoints,
                        RemoveEmbroiderySettings,
                        Reorder,
                        SatinMulticolor,
                        SelectElements,
                        SelectionToGuideLine,
                        SelectionToPattern,
                        SewStackEditor,
                        Simulator,
                        StitchPlanPreview,
                        StitchPlanPreviewUndo,
                        StrokeToLpeSatin,
                        Tartan,
                        TestSwatches,
                        ThreadList,
                        Troubleshoot,
                        UnlinkClone,
                        UpdateSvg,
                        ZigzagLineToSatin,
                        Zip]
