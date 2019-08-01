"""
This testcase is used to test the REST API  in api/caconnector.py
to create, update, delete CA connectors.
"""
from .base import MyApiTestCase
import json
from privacyidea.lib.caconnector import get_caconnector_list, save_caconnector
from privacyidea.lib.policy import set_policy, SCOPE, ACTION, delete_policy
from privacyidea.lib.error import ERROR


class CAConnectorTestCase(MyApiTestCase):

    def test_01_fail_without_auth(self):
        # creation fails without auth
        with self.app.test_request_context('/caconnector/con1',
                                           data={'type': 'localca'},
                                           method='POST'):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)

    def test_02_create_ca_connector(self):
        # create a CA connector
        with self.app.test_request_context('/caconnector/con1',
                                           data={'type': 'local'},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1, result)

        ca_list = get_caconnector_list()
        self.assertEqual(len(ca_list), 1)
        self.assertEqual(ca_list[0].get("connectorname"), "con1")

    def test_03_update_ca_connector(self):
        with self.app.test_request_context('/caconnector/con1',
                                           data={'type': 'local',
                                                 'cakey': '/etc/key.pem',
                                                 'cacert': '/etc/cert.pem'},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1, result)

        ca_list = get_caconnector_list()
        self.assertEqual(len(ca_list), 1)
        self.assertEqual(ca_list[0].get("data"), {u'cacert': u'/etc/cert.pem',
                                                  u'cakey': u'/etc/key.pem'})

    def test_04_read_ca_connector(self):
        with self.app.test_request_context('/caconnector/',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            value = result["value"]
            self.assertEqual(len(value), 1)

        # create a second CA connector
        save_caconnector({"caconnector": "con2",
                          "type": "local"})

        with self.app.test_request_context('/caconnector/',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            value = result["value"]
            self.assertEqual(len(value), 2)

        # cannot read CA connectors anymore if an admin policy is defined
        set_policy("pol_audit", scope=SCOPE.ADMIN, action=ACTION.AUDIT)
        with self.app.test_request_context('/caconnector/',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)

        # need a CACONNECTORREAD policy
        set_policy("pol_ca", scope=SCOPE.ADMIN, action=ACTION.CACONNECTORREAD)
        with self.app.test_request_context('/caconnector/',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            value = result["value"]
            self.assertEqual(len(value), 2)

        # Get only one destinct connector filtered by name
        with self.app.test_request_context('/caconnector/con1',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            value = result["value"]
            self.assertEqual(len(value), 1)
            self.assertEqual(value[0].get("connectorname"), "con1")

        delete_policy("pol_ca")
        delete_policy("pol_audit")

    def test_05_read_as_user(self):
        self.setUp_user_realms()
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username":
                                                     "selfservice@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            at_user = result.get("value").get("token")
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "user", result)
            self.assertEqual(result.get("value").get("realm"), "realm1")

        with self.app.test_request_context('/caconnector/',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            value = result["value"]
            self.assertEqual(len(value), 2)
            self.assertEqual(value[0].get("data"), {})

        # define a USER policy: not allowed to read CA connectors anymore
        set_policy("pol_user", scope=SCOPE.USER, action=ACTION.AUDIT)
        with self.app.test_request_context('/caconnector/',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': at_user}):
            res = self.app.full_dispatch_request()
            self.assertEquals(res.status_code, 403)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertIn("caconnectorread is not allowed", result['error']['message'])

        # ... but we are allowed with a matching policy
        set_policy("pol_caconn", scope=SCOPE.USER, action=ACTION.CACONNECTORREAD)
        with self.app.test_request_context('/caconnector/',
                                           data={},
                                           method='GET',
                                           headers={'Authorization': at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            value = result["value"]
            self.assertEqual(len(value), 2)
            self.assertEqual(value[0].get("data"), {})

        delete_policy("pol_caconn")
        delete_policy("pol_user")

    def test_06_delete_caconnector(self):
        with self.app.test_request_context('/caconnector/con1',
                                           data={},
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            value = result["value"]
            self.assertEqual(value, 1)

        ca_list = get_caconnector_list()
        self.assertEqual(len(ca_list), 1)
        self.assertEqual(ca_list[0].get("connectorname"), "con2")

    def test_07_caconnector_admin_required(self):
        self.authenticate_selfservice_user()

        # As a selfservice user, we are not allowed to delete a CA connector
        with self.app.test_request_context('/caconnector/con1',
                                           data={},
                                           method='DELETE',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEquals(res.status_code, 401)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertFalse(result['status'])
            self.assertEquals(result['error']['code'], ERROR.AUTHENTICATE_MISSING_RIGHT)
            self.assertIn("You do not have the necessary role (['admin']) to access this resource",
                          result['error']['message'])

        # We should get the same error message if a USER policy is defined.
        set_policy("user", scope=SCOPE.USER, action=ACTION.AUDIT, realm="")
        with self.app.test_request_context('/caconnector/con1',
                                           data={},
                                           method='DELETE',
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEquals(res.status_code, 401)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertFalse(result['status'])
            self.assertEquals(result['error']['code'], ERROR.AUTHENTICATE_MISSING_RIGHT)
            self.assertIn("You do not have the necessary role (['admin']) to access this resource",
                          result['error']['message'])

