from senaite.queue import messageFactory as _
from senaite.queue.browser.controlpanel import IQueueControlPanel
from senaite.queue.browser.controlpanel import QueueControlPanelForm

from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.supermodel import model
from plone.z3cform import layout
from zope import schema


class IBikaQueueControlPanel(IQueueControlPanel):
    """Control panel Settings
    """
    model.fieldset(  # noqa model.py exports fieldset dynamically
        'synchronous_processing_cap',
        label=_("Synchronous processing cap"),
        fields=['samples_analyses', 'worksheet_analyses', 'coa_publication']
    )

    samples_analyses = schema.Int(
        title=_("Samples Analyses"),
        description=_(
            "The limits that are specified for the number of Samples Analyses"),
        required=False,
    )

    worksheet_analyses = schema.Int(
        title=_("Worksheet Analyses"),
        description=_(
            "The limits that are specified for the number of Worksheet "
            "Analyses"),
        required=False,
    )
    coa_publication = schema.Bool(
        title=_("COA Publication"),
        description=_(
            "LIMS includes the Publication transition in asynchronous "
            "processing"),
        required=False,
    )


class BikaQueueControlPanelForm(QueueControlPanelForm):
    schema = IBikaQueueControlPanel
    schema_prefix = "senaite.queue"


BikaQueueControlPanelView = layout.wrap_form(BikaQueueControlPanelForm,
                                             ControlPanelFormWrapper)
