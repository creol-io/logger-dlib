"""
Copyright 2019 Cartesi Pte. Ltd.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from threading import Lock
import utils
import os

WAIT_SERVER_TIME = 2

LOGGER = utils.get_new_logger(__name__)
LOGGER = utils.configure_log(LOGGER)


class HashException(Exception):
    pass


class FilePathException(Exception):
    pass


class NotReadyException(Exception):
    pass


class LoggerRegistryManager:

    def __init__(self):
        self.global_lock = Lock()
        self.registry = {}
        self.shutting_down = False

    def submit_file(self, file_path, page_log2_size, tree_log2_size):

        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            err_msg = "The submit file path: {} is not valid".format(file_path)
            LOGGER.error(err_msg)
            raise FilePathException(err_msg)

        (is_ready, result_path) = self.register_action("submit", file_path, page_log2_size, tree_log2_size)

        if not is_ready:
            err_msg = "Result is not yet ready for submit file: {}".format(file_path)
            LOGGER.error(err_msg)
            raise NotReadyException(err_msg)
        else:
            with open(result_path, "r") as f:
                return f.readline()

    def download_file(self, root, page_log2_size, tree_log2_size):

        (is_ready, result_path) = self.register_action("download", root, page_log2_size, tree_log2_size)

        if not is_ready:
            err_msg = "Result is not yet ready for download file: {}".format(root)
            LOGGER.error(err_msg)
            raise NotReadyException(err_msg)
        else:
            return result_path

    """
    Here starts the "internal" API, use the methods bellow taking the right precautions such as holding a lock
    """

    def register_action(self, action, key, page_log2_size, tree_log2_size):

        result_path = "{}.{}".format(key, action)
        # Acquiring global lock and releasing it when completed
        LOGGER.debug("Acquiring registry {} global lock".format(action))
        with self.global_lock:
            LOGGER.debug("Lock acquired")
            if key in self.registry.keys():
                # already contains the key
                if self.registry[key].is_ready:
                    return (True, self.registry[key].result_path)
                else:
                    if os.path.exists(result_path) and os.path.isfile(result_path):
                        self.registry[key].is_ready = True
                        return (True, result_path)
                    else:
                        return (False, "")
            else:
                self.registry[key] = LoggerStatus(result_path)
                command = "python3 simple_logger.py -a {} -p {} -b {} -t {}&".format(action, key, page_log2_size, tree_log2_size)
                LOGGER.info("Issuing: {}...".format(command))
                os.system(command)
                return (False, "")


class LoggerStatus:

    def __init__(self, result_path):
        self.lock = Lock()
        self.result_path = result_path
        self.is_ready = False