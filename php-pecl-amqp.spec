# spec file for php-pecl-amqp
#
# Copyright (c) 2012-2014 Remi Collet
# License: CC-BY-SA
# http://creativecommons.org/licenses/by-sa/3.0/
#
# Please, preserve the changelog entries
#
%{!?php_inidir:  %global php_inidir  %{_sysconfdir}/php.d}
%{!?__pecl:      %global __pecl      %{_bindir}/pecl}
%{!?__php:       %global __php       %{_bindir}/php}

%global with_zts    0%{?__ztsphp:1}
%global with_tests  %{?_with_tests:1}%{!?_with_tests:0}
%global pecl_name   amqp
%global ini_name    %{pecl_name}.ini

Summary:       Communicate with any AMQP compliant server
Name:          php-pecl-amqp
Version:       1.4.0
Release:       1%{?dist}
License:       PHP
Group:         Development/Languages
URL:           http://pecl.php.net/package/amqp
Source0:       http://pecl.php.net/get/%{pecl_name}-%{version}.tgz

BuildRequires: php-devel > 5.2.0
BuildRequires: php-pear
BuildRequires: librabbitmq-devel >= 0.4.1
%if %{with_tests}
BuildRequires: rabbitmq-server
%endif

Requires:         php(zend-abi) = %{php_zend_api}
Requires:         php(api) = %{php_core_api}
Requires(post):   %{__pecl}
Requires(postun): %{__pecl}

Provides:         php-%{pecl_name} = %{version}
Provides:         php-%{pecl_name}%{?_isa} = %{version}
Provides:         php-pecl(%{pecl_name}) = %{version}
Provides:         php-pecl(%{pecl_name})%{?_isa} = %{version}

%if 0%{?fedora} < 20 && 0%{?rhel} < 7
# filter private shared
%{?filter_provides_in: %filter_provides_in %{_libdir}/.*\.so$}
%{?filter_setup}
%endif


%description
This extension can communicate with any AMQP spec 0-9-1 compatible server,
such as RabbitMQ, OpenAMQP and Qpid, giving you the ability to create and
delete exchanges and queues, as well as publish to any exchange and consume
from any queue.


%prep
%setup -q -c
mv %{pecl_name}-%{version}%{?prever} NTS

cd NTS
# Upstream often forget to change this
extver=$(sed -n '/#define PHP_AMQP_VERSION/{s/.* "//;s/".*$//;p}' php_amqp.h)
if test "x${extver}" != "x%{version}"; then
   : Error: Upstream version is ${extver}, expecting %{version}.
   exit 1
fi
cd ..

cat > %{ini_name} << 'EOF'
; Enable %{pecl_name} extension module
extension = %{pecl_name}.so

; http://www.php.net/manual/en/amqp.configuration.php

; Whether calls to AMQPQueue::get() and AMQPQueue::consume()
; should require that the client explicitly acknowledge messages. 
; Setting this value to 1 will pass in the AMQP_AUTOACK flag to
: the above method calls if the flags field is omitted. 
;amqp.auto_ack = 0

; The host to which to connect.
;amqp.host = localhost

; The login to use while connecting to the broker.
;amqp.login = guest

; The password to use while connecting to the broker.
;amqp.password = guest

; The port on which to connect.
;amqp.port = 5672

; The number of messages to prefect from the server during a 
; call to AMQPQueue::get() or AMQPQueue::consume() during which
; the AMQP_AUTOACK flag is not set.
;amqp.prefetch_count = 3

; The virtual host on the broker to which to connect.
;amqp.vhost = /

; Timeout
;amqp.timeout=
;amqp.read_timeout=0
;amqp.write_timeout=0
;amqp.connect_timeout=0
EOF

%if %{with_zts}
cp -pr NTS ZTS
%endif


%build
cd NTS
%{_bindir}/phpize
%configure --with-php-config=%{_bindir}/php-config
make %{?_smp_mflags}

%if %{with_zts}
cd ../ZTS
%{_bindir}/zts-phpize
%configure --with-php-config=%{_bindir}/zts-php-config
make %{?_smp_mflags}
%endif


%install
make -C NTS install INSTALL_ROOT=%{buildroot}

# Drop in the bit of configuration
install -Dpm 644 %{ini_name} %{buildroot}%{php_inidir}/%{ini_name}

# Install XML package description
install -Dpm 644 package.xml %{buildroot}%{pecl_xmldir}/%{name}.xml

%if %{with_zts}
make -C ZTS install INSTALL_ROOT=%{buildroot}
install -Dpm 644 %{ini_name} %{buildroot}%{php_ztsinidir}/%{ini_name}
%endif

# Test & Documentation
cd NTS
for i in $(grep 'role="test"' ../package.xml | sed -e 's/^.*name="//;s/".*$//')
do install -Dpm 644 $i %{buildroot}%{pecl_testdir}/%{pecl_name}/$i
done
for i in $(grep 'role="doc"' ../package.xml | sed -e 's/^.*name="//;s/".*$//')
do install -Dpm 644 $i %{buildroot}%{pecl_docdir}/%{pecl_name}/$i
done


%check
: Minimal load test for NTS extension
%{__php} --no-php-ini \
    --define extension=NTS/modules/%{pecl_name}.so \
    -m | grep %{pecl_name}

%if %{with_zts}
: Minimal load test for ZTS extension
%{__ztsphp} --no-php-ini \
    --define extension=ZTS/modules/%{pecl_name}.so \
    -m | grep %{pecl_name}
%endif

%if %{with_tests}
mkdir log run base
: Launch the RabbitMQ service
export RABBITMQ_PID_FILE=$PWD/run/pid
export RABBITMQ_LOG_BASE=$PWD/log
export RABBITMQ_MNESIA_BASE=$PWD/base
/usr/lib/rabbitmq/bin/rabbitmq-server &>log/output &
/usr/lib/rabbitmq/bin/rabbitmqctl wait $RABBITMQ_PID_FILE

ret=0
pushd NTS
: Run the upstream test Suite for NTS extension
TEST_PHP_EXECUTABLE=%{__php} \
TEST_PHP_ARGS="-n -d extension=$PWD/modules/%{pecl_name}.so" \
NO_INTERACTION=1 \
REPORT_EXIT_STATUS=1 \
%{__php} -n run-tests.php || ret=1
popd

%if %{with_zts}
pushd ZTS
: Run the upstream test Suite for ZTS extension
TEST_PHP_EXECUTABLE=%{__ztsphp} \
TEST_PHP_ARGS="-n -d extension=$PWD/modules/%{pecl_name}.so" \
NO_INTERACTION=1 \
REPORT_EXIT_STATUS=1 \
%{__ztsphp} -n run-tests.php || ret=1
popd
%endif

: Cleanup
if [ -s $RABBITMQ_PID_FILE ]; then
   kill $(cat $RABBITMQ_PID_FILE)
fi
rm -rf log run base

exit $ret
%endif


%post
%{pecl_install} %{pecl_xmldir}/%{name}.xml >/dev/null || :


%postun
if [ $1 -eq 0 ] ; then
    %{pecl_uninstall} %{pecl_name} >/dev/null || :
fi


%files
%doc %{pecl_docdir}/%{pecl_name}
%doc %{pecl_testdir}/%{pecl_name}
%config(noreplace) %{php_inidir}/%{ini_name}
%{php_extdir}/%{pecl_name}.so
%{pecl_xmldir}/%{name}.xml

%if %{with_zts}
%config(noreplace) %{php_ztsinidir}/%{ini_name}
%{php_ztsextdir}/%{pecl_name}.so
%endif


%changelog
* Tue Apr 15 2014 Remi Collet <remi@fedoraproject.org> - 1.4.0-1
- update to 1.6.0 (stable)
- install doc in pecl doc_dir
- install tests in pecl test_dir (in devel)
- add --with tests option to run upstream tests during build
- build ZTS extension

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.2.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Thu May 30 2013 Remi Collet <remi@fedoraproject.org> - 1.2.0-1
- Update to 1.2.0

* Fri Mar 22 2013 Remi Collet <rcollet@redhat.com> - 1.0.9-4
- rebuild for http://fedoraproject.org/wiki/Features/Php55

* Wed Mar 13 2013 Remi Collet <remi@fedoraproject.org> - 1.0.9-3
- rebuild for new librabbitmq

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.9-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Tue Nov 13 2012 Remi Collet <remi@fedoraproject.org> - 1.0.9-1
- update to 1.0.9
- cleanups

* Wed Sep 12 2012 Remi Collet <remi@fedoraproject.org> - 1.0.7-1
- update to 1.0.7

* Mon Aug 27 2012 Remi Collet <remi@fedoraproject.org> - 1.0.5-1
- update to 1.0.5
- LICENSE now provided in upstream tarball

* Wed Aug 01 2012 Remi Collet <remi@fedoraproject.org> - 1.0.4-1
- update to 1.0.4

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.3-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Sat May 19 2012 Remi Collet <remi@fedoraproject.org> - 1.0.3-1
- update to 1.0.3
- add extension version check (and fix)

* Mon Mar 19 2012 Remi Collet <remi@fedoraproject.org> - 1.0.1-3
- clean EL-5 stuff as requires php 5.2.0, https://bugs.php.net/61351

* Sat Mar 10 2012 Remi Collet <remi@fedoraproject.org> - 1.0.1-2
- rebuild for PHP 5.4

* Sat Mar 10 2012 Remi Collet <remi@fedoraproject.org> - 1.0.1-1
- Initial RPM release without ZTS extension
- open request for LICENSE file https://bugs.php.net/61337

