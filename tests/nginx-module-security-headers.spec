#############################################
%global upstream_github GetPageSpeed
%global upstream_name ngx_security_headers
#############################################
%global lastversion_tag x
%global lastversion_dir x
%global upstream_version x
############################################
%if 0%{?plesk}
%define name_prefix sw-
%define nginx_modules_dir %{_datadir}/nginx/modules
%define extradist .pl%{plesk}
%define nginx_load_module load_module nginx/modules
%else
%define name_prefix %{nil}
%define nginx_modules_dir %{_libdir}/nginx/modules
%define extradist %{nil}
%define nginx_load_module load_module modules
%endif

#
%define nginx_user nginx
%define nginx_group nginx

%global main_version %{nginx_version}
%define main_release 1%{?dist}.ngx

%if 0%{?rhel} || 0%{?amzn}
%define _group System Environment/Daemons
BuildRequires: openssl-devel
%endif

%if 0%{?suse_version} == 1315
%define _group Productivity/Networking/Web/Servers
BuildRequires: libopenssl-devel
%define _debugsource_template %{nil}
%endif

%if 0%{?rhel} == 7
%define epoch 1
Epoch: %{epoch}
%define dist .el7
BuildRequires: gcc-c++
BuildRequires: binutils
BuildRequires: make
%define _group System Environment/Daemons
%endif

%if 0%{?rhel} == 8
%define epoch 1
Epoch: %{epoch}
%define _debugsource_template %{nil}
%define dist .el8
BuildRequires: gcc-c++
BuildRequires: binutils
BuildRequires: make
%define _group System Environment/Daemons
%endif

%define bdir %{_builddir}/%{name}-%{main_version}

Summary: NGINX module for adding security headers
Name: %{name_prefix}nginx-module-security-headers
Version: %{main_version}+%{upstream_version}
Release: 2%{?dist}%{extradist}.gps
Vendor: GetPageSpeed, Inc.
URL: https://github.com/GetPageSpeed/ngx_security_headers
Group: %{_group}

Source0: http://nginx.org/download/nginx-%{main_version}.tar.gz
Source100: %{url}/archive/%{lastversion_tag}/%{upstream_name}-%{lastversion_tag}.tar.gz

License: BSD

BuildRoot: %{_tmppath}/%{name}-%{main_version}-%{main_release}-root

BuildRequires: zlib-devel
BuildRequires: pcre-devel
Requires: %{name_prefix}nginx-r%{main_version}

Provides: %{name}-r%{main_version}

%description
This NGINX module adds security headers such as X-Content-Type-Options,
X-Frame-Options, and other important security-related HTTP headers.

%define WITH_CC_OPT $(echo %{optflags} $(pcre-config --cflags))
%define WITH_LD_OPT -Wl,-z,relro -Wl,-z,now

%define BASE_CONFIGURE_ARGS $(echo "--prefix=%{_sysconfdir}/nginx --sbin-path=%{_sbindir}/nginx --modules-path=%{_libdir}/nginx/modules --conf-path=%{_sysconfdir}/nginx/nginx.conf --error-log-path=%{_localstatedir}/log/nginx/error.log --http-log-path=%{_localstatedir}/log/nginx/access.log --pid-path=%{_localstatedir}/run/nginx.pid --lock-path=%{_localstatedir}/run/nginx.lock --http-client-body-temp-path=%{_localstatedir}/cache/nginx/client_temp --http-proxy-temp-path=%{_localstatedir}/cache/nginx/proxy_temp --http-fastcgi-temp-path=%{_localstatedir}/cache/nginx/fastcgi_temp --http-uwsgi-temp-path=%{_localstatedir}/cache/nginx/uwsgi_temp --http-scgi-temp-path=%{_localstatedir}/cache/nginx/scgi_temp --user=%{nginx_user} --group=%{nginx_group} --with-compat --with-file-aio --with-threads --with-http_addition_module --with-http_auth_request_module --with-http_dav_module --with-http_flv_module --with-http_gunzip_module --with-http_gzip_static_module --with-http_mp4_module --with-http_random_index_module --with-http_realip_module --with-http_secure_link_module --with-http_slice_module --with-http_ssl_module --with-http_stub_status_module --with-http_sub_module --with-http_v2_module --with-mail --with-mail_ssl_module --with-stream --with-stream_realip_module --with-stream_ssl_module --with-stream_ssl_preread_module")
%define MODULE_CONFIGURE_ARGS $(echo "--add-dynamic-module=%{lastversion_dir}")

%prep
%setup -qcTn %{name}-%{main_version}
tar --strip-components=1 -zxf %{SOURCE0}
tar xzf %SOURCE100

%build
cd %{bdir}
./configure %{BASE_CONFIGURE_ARGS} %{MODULE_CONFIGURE_ARGS} \
	--with-cc-opt="%{WITH_CC_OPT}" \
	--with-ld-opt="%{WITH_LD_OPT}"
make %{?_smp_mflags} modules

%install
cd %{bdir}
%{__rm} -rf $RPM_BUILD_ROOT
%{__mkdir} -p $RPM_BUILD_ROOT%{_datadir}/doc/%{name}
%{__install} -m 644 -p %{lastversion_dir}/LICENSE \
    $RPM_BUILD_ROOT%{_datadir}/doc/%{name}/
%{__install} -m 644 -p %{lastversion_dir}/README.md \
    $RPM_BUILD_ROOT%{_datadir}/doc/%{name}/
%{__mkdir} -p $RPM_BUILD_ROOT%{nginx_modules_dir}
for so in `find %{bdir}/objs/ -maxdepth 1 -type f -name "*.so"`; do
%{__install} -m755 $so \
   $RPM_BUILD_ROOT%{nginx_modules_dir}
done

%check
%{__rm} -rf $RPM_BUILD_ROOT/usr/src
cd %{bdir}
grep -v 'usr/src' debugfiles.list > debugfiles.list.new && mv debugfiles.list.new debugfiles.list
cat /dev/null > debugsources.list
%if 0%{?suse_version} >= 1500
cat /dev/null > debugsourcefiles.list
%endif

%clean
%{__rm} -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%{nginx_modules_dir}/*
%dir %{_datadir}/doc/%{name}
%{_datadir}/doc/%{name}/*

%changelog
# no changelog
