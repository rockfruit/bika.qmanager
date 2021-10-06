# -*- coding: utf-8 -*-

import json
import six
import base64
from plone import api as ploneapi
from zope.component import getAdapters
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse

from bika.lims import api
from bika.lims import bikaMessageFactory as _
from bika.lims.browser.analysisrequest.add2 import ajaxAnalysisRequestAddView as aARAV
from bika.lims.interfaces import IAddSampleRecordsValidator
from senaite.queue import api as q_api


class ajaxAnalysisRequestAddView(aARAV):
    """ Overrides ajaxAnalysisRequestAddView.ajax_submit to submit the form of
        Samples(ARs) creation and sends the Samples to be created on
        senaite.queue
    """

    implements(IPublishTraverse)

    def ajax_submit(self):
        # samples folder
        # Check if there is the need to display a confirmation pane
        confirmation = self.check_confirmation()
        if confirmation:
            return {"confirmation": confirmation}

        # Get AR required fields (including extended fields)
        fields = self.get_ar_fields()

        # extract records from request
        records = self.get_records()

        fielderrors = {}
        errors = {"message": "", "fielderrors": {}}

        attachments = {}
        valid_records = []

        # Validate required fields
        for n, record in enumerate(records):

            # Process textfield fields first and set their values to the linked field
            # NOTE: Quickfix for RejectionReasons.textfield
            text_fields = filter(lambda f: f.endswith(".textfield"), record)
            for field in text_fields:
                name = field.replace(".textfield", "")
                value = record.get(field)
                for i in value:
                    value[value.index(i)] = dict(i)
                    record[name] = value

            # Process UID fields first and set their values to the linked field
            uid_fields = filter(lambda f: f.endswith("_uid"), record)
            for field in uid_fields:
                name = field.replace("_uid", "")
                value = record.get(field)
                if "," in value:
                    value = value.split(",")
                record[name] = value

            # Extract file uploads (fields ending with _file)
            # These files will be added later as attachments
            file_fields = filter(lambda f: f.endswith("_file"), record)
            attachments[n] = map(lambda f: record.pop(f), file_fields)

            # Required fields and their values
            required_keys = [field.getName() for field in fields if field.required]
            required_values = [record.get(key) for key in required_keys]
            required_fields = dict(zip(required_keys, required_values))

            # Client field is required but hidden in the AR Add form. We remove
            # it therefore from the list of required fields to let empty
            # columns pass the required check below.
            if record.get("Client", False):
                required_fields.pop("Client", None)

            # Contacts get pre-filled out if only one contact exists.
            # We won't force those columns with only the Contact filled out to
            # be required.
            contact = required_fields.pop("Contact", None)

            # None of the required fields are filled, skip this record
            if not any(required_fields.values()):
                continue

            # Re-add the Contact
            required_fields["Contact"] = contact

            # Check if the contact belongs to the selected client
            contact_obj = api.get_object(contact, None)
            if not contact_obj:
                fielderrors["Contact"] = _("No valid contact")
            else:
                parent_uid = api.get_uid(api.get_parent(contact_obj))
                if parent_uid != record.get("Client"):
                    msg = _("Contact does not belong to the selected client")
                    fielderrors["Contact"] = msg

            # Missing required fields
            missing = [f for f in required_fields if not record.get(f, None)]

            # If there are required fields missing, flag an error
            for field in missing:
                fieldname = "{}-{}".format(field, n)
                msg = _("Field '{}' is required".format(field))
                fielderrors[fieldname] = msg

            # Process valid record
            valid_record = dict()
            for fieldname, fieldvalue in six.iteritems(record):
                # clean empty
                if fieldvalue in ["", None]:
                    continue
                valid_record[fieldname] = fieldvalue

            # append the valid record to the list of valid records
            attachs = []
            for attachment in attachments.get(n, []):
                filename = attachment.filename
                if not filename:
                    continue
                headers = attachment.headers.dict
                data = {
                    "title": n,
                    "file": {
                        "encoding": "base64",
                        "filename": filename,
                        "content-type": headers["content-type"],
                    },
                }
                with open(attachment.name, mode="rb") as myfile:
                    img = attachment.file.read()
                    data["file"]["data"] = base64.b64encode(img)
                    attachs.append(json.dumps(data))
            valid_record["attachments"] = attachs
            valid_records.append(valid_record)

        # return immediately with an error response if some field checks failed
        if fielderrors:
            errors["fielderrors"] = fielderrors
            return {"errors": errors}

        # do a custom validation of records. For instance, we may want to rise
        # an error if a value set to a given field is not consistent with a
        # value set to another field
        validators = getAdapters((self.request,), IAddSampleRecordsValidator)
        for name, validator in validators:
            validation_err = validator.validate(valid_records)
            if validation_err:
                # Not valid, return immediately with an error response
                return {"errors": validation_err}

        samples_analyses = ploneapi.portal.get_registry_record(
            "senaite.queue.samples_analyses"
        )
        count = 0
        for i in valid_records:
            count += len(i["Analyses"])
        if samples_analyses > count:
            return super(ajaxAnalysisRequestAddView, self).ajax_submit()

        params = {"records": valid_records}
        q_api.add_task("bika.qmanager.create_ars", self.context, **params)
        return {"success": ""}
