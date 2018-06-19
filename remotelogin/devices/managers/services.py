import fdutils
from .base import Manager
import logging
log = logging.getLogger(__name__)


class ServicesManager(Manager):

    def __init__(self, *args, **kwargs):
        self.services = {}
        super(ServicesManager, self).__init__(*args, **kwargs)

    def add_service(self, service, assign_name='', use_svc_name=False):
        """ Adds a service to this device and creates an attribute called assign_name, if given, or
            svc_ + name of the service (given by the function svc_name in service)

        :param services.base.Service service: a service (eg Site) to add to the services offered by this device
        :param str assign_name: if given, this will be the name of the attribute on the device.

        """
        session_mgr = SessionManager(service)
        if session_mgr.already_assigned_to_device(self):
            raise ValueError('Service already assigned')

        if session_mgr.host is None:
            session_mgr.set_host(self.host)

        service_name = 'svc_' + session_mgr.svc_name()
        if not assign_name and not use_svc_name:
            setattr(self, service_name, session_mgr)
        else:
            assign_name = assign_name if assign_name else session_mgr.name
            if assign_name in self.__dict__:
                log.error('The provided assigned name {} already exist in the device attribute'.format(assign_name))
                raise ValueError('Provided attribute name "{}" already in used'.format(assign_name))
            setattr(self, assign_name, session_mgr)
            service_name = assign_name

        service.name_assigned_on_device = service_name
        service.device_assigned_to = self
        if hasattr(service, 'download_folder'):
            service.download_folder = self.folder
        self._services.append(service_name)
        self.add_capability(session_mgr.send)

        return session_mgr

    def remove_service(self, service):
        """ removes a service from this device

        :param Service service: a string or service object

        """
        try:
            if not service.already_assigned_to_device() or not hasattr(self, service.name_assigned_on_device):
                log.error('This Service ({}) has not been assigned to any device'.format(service.name))
                return

            getattr(self, service.name_assigned_on_device).close()
            delattr(self, service.name_assigned_on_device)
            service.remove_from_device()
            fdutils.lists.del_from_list(self._services, [service.name_assigned_on_device])
            self.remove_capability(service.send)
        except:
            pass

    def new_session_service_type(self, service_type, session_name='', **kwargs):
        svc = self.get_service_with_type(service_type)
        if not isinstance(svc, sessions.SessionManager):
            raise AttributeError('This service type ({}) did not return a session object.'.format(service_type))

        return svc.new_session(session_name, **kwargs)

    def close(self):
        for s in self._services:
            self.remove_service(s)

    def get_services(self):
        """ Retrieve the service names added to this device (eg. svc_site_google)

        :return:
        """
        return self._services

    # TODO: deprecate this for get_service_with_type
    def get_service(self, svc_class, service_name):
        """ returns the service attribute, if exists, given the service class and the name.  This will only find service that have been
            added using defaults (i.e not using assign_name in add_service). It will raise an error if the name is not present

        :param Service svc_class: service class to look for
        :param str service_name: the name
        :raise: AttributeError

        """
        return getattr(self, 'svc_' + svc_class.SVC_PREPEND + '_' + service_name)

    def has_service(self, service_type):
        """ check weather the device has a particular type of service

        :param service_type:
        :return:
        """
        return bool(self.get_service_with_type(service_type))

    def get_services_with_type(self, service_type):
        """ retrieves a list of services assigned on this device that are of a certain type

        :param service_type: type of device we are looking for
        :return: list of services or empty list if no services of this kind were found
        :rtype: list of test_utils.Service
        """
        ret = []
        for svc_name in self._services:
            if hasattr(self, svc_name):
                e = getattr(self, svc_name)
                if isinstance(e, service_type) or (isinstance(e, sessions.SessionManager) and isinstance(e.managed_object, service_type)):
                    ret.append(e)
        return ret

    def get_service_with_type(self, service_type):
        """ retrieves a single service (first one found of the type service_type)

        :param Service service_type: name of the type of service
        :return:
        """
        svc = self.get_services_with_type(service_type)
        if len(svc) > 1:
            raise NonUniqueServiceError('There is more than one service of type {} in this RDU {}. Maybe you meant get_services_with_type (with s)'.format(service_type, self.name))
        if not svc:
            raise ServiceNotFoundError('This device does not have a service with type ' + service_type.__name__)
        return svc[0]