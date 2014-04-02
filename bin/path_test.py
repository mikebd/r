from config_test import ConfigTestCase
import os
import path
import shutil

temp_tempdir_segment = None


class PathTestCase(ConfigTestCase):

    @classmethod
    def setUpClass(cls):
        ConfigTestCase.setUpClass()
        global temp_tempdir_segment
        temp_tempdir_segment = path.tempdir_segment
        path.tempdir_segment = 'r_test'

    @classmethod
    def tearDownClass(cls):
        path.tempdir_segment = temp_tempdir_segment
        ConfigTestCase.tearDownClass()

    def setUp(self):
        p = path.get_temp_path()
        if os.path.exists(p):
            shutil.rmtree(p)
        #os.makedirs(p)