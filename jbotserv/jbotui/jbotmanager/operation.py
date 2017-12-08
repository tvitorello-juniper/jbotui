"""Module provides the operation class, which provides an object representation for the procedure,
as well as a method to convert the procedure to the YAML string format.
"""

import os

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from jbotui.models import Jsnap
from jbotui.models import JunosImage
from jbotserv.settings import MEDIA_ROOT

class OPError(Exception):
    pass

class Operation(object):
    """The operation object represents the JBOT procedure. During the object initialization, the
    construtor checks for all the required information for the operation. Should there be missing
    data, the constructor raises an error. This object also provides a method for retriving the
    string representation of the operation to print to the YAML file.
    """

    def get_procedure(self):
        """Returns the YAML string representation of the procedure.

        Args:
            None
        Returns:
            procedure_string: A YAML string representation of the procedure.
        """
        return self.procedure

    def __init__(self, procedure_id, title, set_dict):

        project_root, _ = os.path.dirname(MEDIA_ROOT).split("media")

        self.title = title

        self.procedure = ""

        #-------------------------------------------------------------------------------------------
        # Start Operation
        #-------------------------------------------------------------------------------------------
        if title == "Start":
            return

        #-------------------------------------------------------------------------------------------
        # End Operation
        #-------------------------------------------------------------------------------------------
        if title == "End":
            # Build the procedure string
            self.procedure = procedure_id + ":\n  end:\n  <<: *defaults\n"

        #-------------------------------------------------------------------------------------------
        # Fail Operation
        #-------------------------------------------------------------------------------------------
        if title == "Fail":
            # Build the procedure string
            self.procedure = procedure_id + ":\n  end_failure:\n"

        #-------------------------------------------------------------------------------------------
        # Take Snapshot Operation
        #-------------------------------------------------------------------------------------------
        elif title == "Take Snapshot":
            try:
                snapshot_name = set_dict['take_snapshot_name']
                file_type = set_dict['take_compare_type']
                if file_type == "pre":
                    jsnap_name = set_dict['take_pre_name']
                elif file_type == "custom":
                    jsnap_name = set_dict['take_custom_name']
                else:
                    raise OPError("Incomplete Take Snapshot parameters.")
            except KeyError:
                raise OPError("Incomplete Take Snapshot parameters.")
            jsnap_test = get_jsnap_path(jsnap_name)
            self.procedure = procedure_id + ":\n  jsnap:\n    type: snap\n    test: " + \
                jsnap_test + "\n    snap_type: snap\n    argument: " + snapshot_name + \
                "\n  <<: *defaults\n"

        #-------------------------------------------------------------------------------------------
        # Compare Snapshots Operation
        #-------------------------------------------------------------------------------------------
        elif title == "Compare Snapshots":
            #---------------------------------------------------------------------------------------
            # Recover the names of the snapshots to be compared
            try:
                snapshot1 = set_dict['snapshot1name']
                snapshot2 = set_dict['snapshot2name']
            except KeyError:
                raise OPError(\
                "Could not retrieve one or both of the snapshots names to be compared.")
            argument = snapshot1 + "," + snapshot2
            #---------------------------------------------------------------------------------------
            # Recover the type of comparison
            try:
                compare_type = set_dict['comparetype']
            except KeyError:
                raise OPError("Could not retrieve snapshot comparison type.")
            #---------------------------------------------------------------------------------------
            # Preconfigured Comparison
            if compare_type == "pre":
                #-----------------------------------------------------------------------------------
                # Get JSNAP comparison file name
                try:
                    compare_file_name = set_dict['precomparefile']
                except KeyError:
                    raise OPError("Could not retrieve snapshot comparison file.")
                compare_file = get_jsnap_path(compare_file_name)
                #-----------------------------------------------------------------------------------
                # Build the procedure string
                self.procedure = procedure_id + ":\n  jsnap:\n    type: check\n    test: " + \
                    compare_file + "\n    snap_type: check\n    argument: " + argument + \
                    "\n    mode: strict\n  <<: *defaults\n"

            #---------------------------------------------------------------------------------------
            # Custom Comparison
            if compare_type == "custom":
                print "Custom compare"
                try:
                    compare_file_name = set_dict['snapconfigfile']
                    compare_file = get_jsnap_path(compare_file_name)
                except KeyError:
                    raise OPError("Could not retrieve custom snapshot comparison file.")
                #-----------------------------------------------------------------------------------
                # Build the procedure string
                self.procedure = procedure_id + ":\n  jsnap:\n    type: check\n    test: " + \
                    compare_file + "\n    snap_type: check\n    argument: " + argument + \
                    "\n    mode: strict\n  <<: *defaults\n"

        #-------------------------------------------------------------------------------------------
        # Upgrade Operation
        #-------------------------------------------------------------------------------------------
        elif title == "Upgrade":
            #---------------------------------------------------------------------------------------
            # Recover filepath
            try:
                filepath = set_dict['upgradefilepath']
            except KeyError:
                raise OPError("Could not retrieve upgrade file path.")
            #---------------------------------------------------------------------------------------
            # Find the RE where the sw package is going to be added
            try:
                target_re = set_dict['upgradetargetRE']
            except KeyError:
                raise OPError("Could not retrieve target RE.")
            #---------------------------------------------------------------------------------------
            # Build the procedure string
            self.procedure = procedure_id + ":\n  add_sw_package:\n    version: /var/tmp/" + filepath + \
                "\n    validate: True\n    role: " + target_re + "\n  <<: *defaults\n"
            #---------------------------------------------------------------------------------------
            # Add a reboot command for single RE
            if target_re == "single":
                self.procedure = self.procedure + str(int(procedure_id) + 1) + \
                    ":\n  reboot_RE:\n" + "    role: single\n  <<: *defaults\n"

        #-------------------------------------------------------------------------------------------
        # Reboot Operation
        #-------------------------------------------------------------------------------------------
        elif title == "Reboot":
            #---------------------------------------------------------------------------------------
            # Find the RE to be rebooted
            try:
                target_re = set_dict['reboottargetRE']
            except KeyError:
                raise OPError("Could not retrieve target RE to reboot.")
            #---------------------------------------------------------------------------------------
            # Build the procedure string
            self.procedure = procedure_id + ":\n  reboot_RE:\n    role: " + target_re + \
                "\n  <<: *defaults\n"

        #-------------------------------------------------------------------------------------------
        # Switchover Operation
        #-------------------------------------------------------------------------------------------
        elif title == "Switchover":
            #---------------------------------------------------------------------------------------
            # Build the procedure string
            self.procedure = procedure_id + ":\n  switchover:\n  <<: *defaults\n"

        #-------------------------------------------------------------------------------------------
        # Send Image Operation
        #-------------------------------------------------------------------------------------------
        elif title == "Send Image":
            #---------------------------------------------------------------------------------------
            # Find the image to be send to the device
            try:
                target_image = set_dict['junosimage']
            except KeyError:
                raise OPError("Could not retrieve target image name.")
            #---------------------------------------------------------------------------------------
            # Recover image from the the DB
            image_path = get_image_path(target_image)
            #---------------------------------------------------------------------------------------
            # Build the procedure string
            self.procedure = procedure_id + ":\n  scp_package:\n    package: " + image_path + \
                "\n  <<: *defaults\n"

def get_image_path(image_name):
    """Retrieves the absolute path to the Junos image with the specified name. Returns None if 
    there is no image with such name present in the database.abs

    Args:
        image_name: a string contianing the image name.

    Returns:
        image_path: absolute path to the image located within the database.

    """

    try:
        entry = JunosImage.objects.get(data="images/" + image_name)
        return MEDIA_ROOT + str(entry.data)
    except ObjectDoesNotExist:
        raise OPError("Could not locate image '" + image_name + "' within the server database.")
    except MultipleObjectsReturned:
        raise OPError("Multiple images '" + image_name + "' located within the server database.")

def get_jsnap_path(jsnap_name):
    """Retrieves the path relative to the media folder for the jsnap name specified. Returns None
    if there is no such file with the specified name.abs

    Args:
        jsnap_name: a string containing the Jsnap file name.

    Returns:
        jsnap_path: relative path to the Jsnap file located within the database.

    """

    if jsnap_name[-6:] != '.jsnap':
        jsnap_name += '.jsnap'
    try:
        jsnap_entry = Jsnap.objects.get(data="tests/" + jsnap_name)
    except ObjectDoesNotExist:
        raise OPError("Unable to locate a Jsnap file with the name: '" + jsnap_name + "'")
    except MultipleObjectsReturned:
        raise OPError("Multiple entries for the specified Jsnap file name: '" + jsnap_name + "'")
    return 'media/' + str(jsnap_entry.data)
