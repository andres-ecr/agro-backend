from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from tenants.models import Tenant

User = get_user_model()


class UserStatusHierarchyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='Ica', code='status-ica')
        cls.other_tenant = Tenant.objects.create(name='Casma', code='status-casma')
        cls.accounts = {}
        for role in ['superadmin', 'admin', 'supervisor', 'operator']:
            cls.accounts[role] = User.objects.create_user(
                email=f'{role}@status.test', role=role, tenant=cls.tenant,
                first_name=role, last_name='Test',
            )

    def setUp(self):
        self.client = APIClient()

    def test_all_roles_can_only_change_strictly_subordinate_status(self):
        roles = ['superadmin', 'admin', 'supervisor', 'operator']
        for actor_index, actor_role in enumerate(roles):
            self.client.force_authenticate(self.accounts[actor_role])
            for target_index, target_role in enumerate(roles):
                target = self.accounts[target_role]
                target.is_active = True
                target.save(update_fields=['is_active'])
                with self.subTest(actor=actor_role, target=target_role):
                    response = self.client.patch(f'/users/{target.pk}/', {'is_active': False})
                    allowed = target_index > actor_index
                    if allowed:
                        self.assertEqual(response.status_code, 200)
                    else:
                        self.assertIn(response.status_code, [403, 404])
                    target.refresh_from_db()
                    self.assertEqual(target.is_active, not allowed)

    def test_same_role_peer_and_self_cannot_be_modified_or_deleted(self):
        for role, actor in self.accounts.items():
            peer = User.objects.create_user(email=f'peer-{role}@status.test', role=role, tenant=self.tenant)
            self.client.force_authenticate(actor)
            for target in [actor, peer]:
                for method in [self.client.patch, self.client.delete]:
                    response = method(f'/users/{target.pk}/', {'is_active': False})
                    self.assertIn(response.status_code, [403, 404])
                    self.assertTrue(User.objects.filter(pk=target.pk, is_active=True).exists())

    def test_local_managers_cannot_cross_tenants_even_with_header(self):
        foreign = User.objects.create_user(email='foreign@status.test', role='operator', tenant=self.other_tenant)
        for role in ['admin', 'supervisor']:
            self.client.force_authenticate(self.accounts[role])
            for method in [self.client.patch, self.client.delete]:
                response = method(f'/users/{foreign.pk}/', {'is_active': False}, HTTP_X_TENANT_ID=str(self.other_tenant.pk))
                self.assertEqual(response.status_code, 403 if role == 'supervisor' and method == self.client.delete else 404)
                self.assertTrue(User.objects.filter(pk=foreign.pk, is_active=True).exists())

    def test_supervisor_can_list_subordinates_but_cannot_edit_other_fields(self):
        self.client.force_authenticate(self.accounts['supervisor'])
        response = self.client.get('/users/')
        self.assertEqual(response.status_code, 200)
        results = response.data.get('results', response.data)
        self.assertIn(self.accounts['operator'].pk, [row['id'] for row in results])
        target = self.accounts['operator']
        for payload in [{'is_active': False, 'role': 'admin'}, {'first_name': 'changed'}, {'is_active': False, 'tenant': self.other_tenant.pk}, {'is_active': False, 'is_superuser': True}]:
            self.assertEqual(self.client.patch(f'/users/{target.pk}/', payload).status_code, 403)
        self.assertEqual(self.client.put(f'/users/{target.pk}/', {'email': target.email, 'is_active': False}).status_code, 403)
        target.refresh_from_db()
        self.assertTrue(target.is_active)
        self.assertEqual(target.role, 'operator')

    def test_admin_cannot_bypass_hierarchy_with_privilege_or_role_payload(self):
        self.client.force_authenticate(self.accounts['admin'])
        target = self.accounts['operator']
        for payload in [{'is_active': False, 'is_superuser': True}, {'is_active': False, 'role': 'admin'}]:
            self.assertEqual(self.client.patch(f'/users/{target.pk}/', payload).status_code, 403)
        target.refresh_from_db()
        self.assertFalse(target.is_superuser)
        self.assertTrue(target.is_active)

    def test_status_patch_preserves_identity_and_row(self):
        self.client.force_authenticate(self.accounts['admin'])
        target = self.accounts['operator']
        response = self.client.patch(f'/users/{target.pk}/', {'is_active': False})
        self.assertEqual(response.status_code, 200)
        target.refresh_from_db()
        self.assertFalse(target.is_active)
        self.assertEqual(target.email, 'operator@status.test')
        self.assertEqual(target.role, 'operator')
        self.assertEqual(target.tenant, self.tenant)

    def test_supervisor_can_change_status_but_cannot_permanently_delete_operator(self):
        self.client.force_authenticate(self.accounts['supervisor'])
        target = self.accounts['operator']
        self.assertEqual(self.client.delete(f'/users/{target.pk}/').status_code, 403)
        target.refresh_from_db()
        self.assertTrue(target.is_active)
        self.assertEqual(self.client.patch(f'/users/{target.pk}/', {'is_active': False}).status_code, 200)
        target.refresh_from_db()
        self.assertFalse(target.is_active)

    def test_self_profile_and_created_privileges_cannot_bypass_hierarchy(self):
        self.client.force_authenticate(self.accounts['admin'])
        response = self.client.patch('/auth/me/', {'is_active': False})
        self.assertEqual(response.status_code, 200)
        self.accounts['admin'].refresh_from_db()
        self.assertTrue(self.accounts['admin'].is_active)
        response = self.client.post('/users/', {
            'email': 'privileged@status.test', 'password': 'Password123!',
            'first_name': 'Test', 'last_name': 'User', 'role': 'operator', 'is_superuser': True,
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(email='privileged@status.test').exists())

    def test_superadmin_can_manage_subordinate_in_another_site(self):
        target = User.objects.create_user(email='global@status.test', role='admin', tenant=self.other_tenant)
        self.client.force_authenticate(self.accounts['superadmin'])
        self.assertEqual(self.client.patch(f'/users/{target.pk}/', {'is_active': False}).status_code, 200)
        target.refresh_from_db()
        self.assertFalse(target.is_active)
        for payload in [{'role': 'superadmin'}, {'is_superuser': True}]:
            self.assertEqual(self.client.patch(f'/users/{target.pk}/', payload).status_code, 403)

    def test_managers_without_assigned_site_cannot_manage_local_users(self):
        for role in ['admin', 'supervisor']:
            actor = self.accounts[role]
            actor.tenant = None
            actor.save(update_fields=['tenant'])
            self.client.force_authenticate(actor)
            response = self.client.patch(f'/users/{self.accounts["operator"].pk}/', {'is_active': False})
            self.assertEqual(response.status_code, 404)


class UserHierarchyAndRoleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant_ica = Tenant.objects.create(name='Sede Ica', code='ica')
        self.tenant_casma = Tenant.objects.create(name='Sede Casma', code='casma')

        self.superadmin = User.objects.create_user(
            email='super@agro.com',
            password='Password123!',
            first_name='Super',
            last_name='Admin',
            role='superadmin',
            tenant=self.tenant_ica,
            is_superuser=True,
            is_staff=True,
        )

        self.admin_ica = User.objects.create_user(
            email='admin.ica@agro.com',
            password='Password123!',
            first_name='Admin',
            last_name='Ica',
            role='admin',
            tenant=self.tenant_ica,
        )

        self.operator_ica = User.objects.create_user(
            email='op.ica@agro.com',
            password='Password123!',
            first_name='Operator',
            last_name='Ica',
            role='operator',
            tenant=self.tenant_ica,
        )

        self.operator_casma = User.objects.create_user(
            email='op.casma@agro.com',
            password='Password123!',
            first_name='Operator',
            last_name='Casma',
            role='operator',
            tenant=self.tenant_casma,
        )

    def test_token_obtain_pair_returns_role_and_tenant(self):
        response = self.client.post('/auth/token/', {
            'email': 'super@agro.com',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        user_data = response.data['user']
        self.assertEqual(user_data['role'], 'superadmin')
        self.assertTrue(user_data['is_superuser'])
        self.assertEqual(user_data['tenant']['code'], 'ica')

    def test_superadmin_user_list_all_and_filter_by_tenant(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get('/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        # Should return all users
        emails = [u['email'] for u in results]
        self.assertIn('super@agro.com', emails)
        self.assertIn('admin.ica@agro.com', emails)
        self.assertIn('op.ica@agro.com', emails)
        self.assertIn('op.casma@agro.com', emails)

        # Filter by tenant Casma
        response_filtered = self.client.get(f'/auth/users/?tenant={self.tenant_casma.id}')
        self.assertEqual(response_filtered.status_code, status.HTTP_200_OK)
        filtered_results = response_filtered.data.get('results', response_filtered.data)
        filtered_emails = [u['email'] for u in filtered_results]
        self.assertIn('op.casma@agro.com', filtered_emails)
        self.assertNotIn('op.ica@agro.com', filtered_emails)

    def test_admin_user_list_scoped_to_tenant_excluding_superadmin(self):
        self.client.force_authenticate(user=self.admin_ica)
        response = self.client.get('/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        emails = [u['email'] for u in results]
        self.assertNotIn('super@agro.com', emails)
        self.assertIn('admin.ica@agro.com', emails)
        self.assertIn('op.ica@agro.com', emails)
        self.assertNotIn('op.casma@agro.com', emails)

    def test_admin_cannot_create_superadmin(self):
        self.client.force_authenticate(user=self.admin_ica)
        response = self.client.post('/auth/users/', {
            'email': 'hacker@agro.com',
            'password': 'Password123!',
            'first_name': 'Hacker',
            'last_name': 'Super',
            'role': 'superadmin',
            'tenant': self.tenant_casma.id,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_creates_operator_forces_own_tenant(self):
        self.client.force_authenticate(user=self.admin_ica)
        response = self.client.post('/auth/users/', {
            'email': 'new.operator@agro.com',
            'password': 'Password123!',
            'first_name': 'New',
            'last_name': 'Operator',
            'role': 'operator',
            'tenant': self.tenant_casma.id,  # Attempting to assign casma
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_user = User.objects.get(email='new.operator@agro.com')
        # Tenant must be forced to admin's tenant (Ica)
        self.assertEqual(new_user.tenant, self.tenant_ica)

    def test_admin_cannot_create_role_not_allowed_for_tenant(self):
        self.tenant_ica.allowed_roles = ['admin', 'operator']
        self.tenant_ica.save()
        self.client.force_authenticate(user=self.admin_ica)

        # Attempt to create supervisor
        response = self.client.post('/auth/users/', {
            'email': 'supervisor.ica@agro.com',
            'password': 'Password123!',
            'first_name': 'Supervisor',
            'last_name': 'Ica',
            'role': 'supervisor',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role', response.data)

    def test_admin_cannot_update_role_to_disallowed_role(self):
        self.tenant_ica.allowed_roles = ['admin', 'operator']
        self.tenant_ica.save()
        self.client.force_authenticate(user=self.admin_ica)

        # Attempt to update operator to supervisor
        response = self.client.patch(f'/auth/users/{self.operator_ica.id}/', {
            'role': 'supervisor',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role', response.data)

    def test_me_view_get_and_patch(self):
        self.client.force_authenticate(user=self.operator_ica)
        
        # Test GET /auth/me/
        get_res = self.client.get('/auth/me/')
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(get_res.data['email'], 'op.ica@agro.com')
        self.assertEqual(get_res.data['first_name'], 'Operator')

        # Test PATCH /auth/me/
        patch_res = self.client.patch('/auth/me/', {
            'first_name': 'Operario Actualizado',
            'last_name': 'Ica Modificado',
        })
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data['first_name'], 'Operario Actualizado')
        self.assertEqual(patch_res.data['last_name'], 'Ica Modificado')

        # Verify persisted in database
        self.operator_ica.refresh_from_db()
        self.assertEqual(self.operator_ica.first_name, 'Operario Actualizado')
        self.assertEqual(self.operator_ica.last_name, 'Ica Modificado')

    def test_change_password_post(self):
        self.client.force_authenticate(user=self.operator_ica)

        # Test POST with missing current password
        fail_res = self.client.post('/auth/change-password/', {
            'password': 'NewSecurePassword456!',
        })
        self.assertEqual(fail_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_password', fail_res.data)

        # Test POST with incorrect current password
        wrong_old_res = self.client.post('/auth/change-password/', {
            'current_password': 'WrongPassword!',
            'password': 'NewSecurePassword456!',
        })
        self.assertEqual(wrong_old_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_password', wrong_old_res.data)

        # Test POST with valid current password and valid new password
        success_res = self.client.post('/auth/change-password/', {
            'current_password': 'Password123!',
            'password': 'NewSecurePassword456!',
        })
        self.assertEqual(success_res.status_code, status.HTTP_200_OK)

        # Verify password check
        self.operator_ica.refresh_from_db()
        self.assertTrue(self.operator_ica.check_password('NewSecurePassword456!'))


