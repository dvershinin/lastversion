#############################################
%global upstream_github google
#############################################
%global lastversion_tag x
%global lastversion_dir x
############################################

%if 0%{?rhel} > 7
# Disable python2 build by default
%bcond_with python2
%else
%bcond_without python2
%endif

%if 0%{?amzn} == 2
# Aug 27 2020: Amazon Linux shipped Python 3 packages with names python-devel for Python 3.7
%global python3_pkgversion 3
%endif

Name: brotli
Version: 2.0.0
Release: 1%{?dist}
Summary:        Lossless compression algorithm

License:        MIT
URL:            https://github.com/%{upstream_github}/%{name}
Source0:        %{url}/archive/%{lastversion_tag}/%{name}-%{lastversion_tag}.tar.gz
# Python bindings are not in release tarball (.gitattributes)
#Source2:        https://files.pythonhosted.org/packages/9b/2f/29ec65c7497e4d50f3cd60c336a526f1cf1fe71cbc66beb70a5a2f5b7f8b/Brotli-1.0.8.zip
#BuildRequires: unzip

%if %{with python2}
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
%endif
BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  python%{python3_pkgversion}-setuptools
BuildRequires:  gcc-c++ gcc cmake

%description
Brotli is a generic-purpose lossless compression algorithm that compresses
data using a combination of a modern variant of the LZ77 algorithm, Huffman
coding and 2nd order context modeling, with a compression ratio comparable
to the best currently available general-purpose compression methods.
It is similar in speed with deflate but offers more dense compression.

%if %{with python2}
%package -n python2-%{name}
Summary:        Lossless compression algorithm (python 2)
Requires: python2
%{?python_provide:%python_provide python2-%{name}}

%description -n python2-%{name}
Brotli is a generic-purpose lossless compression algorithm that compresses
data using a combination of a modern variant of the LZ77 algorithm, Huffman
coding and 2nd order context modeling, with a compression ratio comparable
to the best currently available general-purpose compression methods.
It is similar in speed with deflate but offers more dense compression.
This package installs a Python 2 module.
%endif


%package -n python%{python3_pkgversion}-%{name}
Requires: python%{python3_pkgversion}
Summary:        Lossless compression algorithm (python 3)
%{?python_provide:%python_provide python%{python3_pkgversion}-%{name}}

%description -n python%{python3_pkgversion}-%{name}
Brotli is a generic-purpose lossless compression algorithm that compresses
data using a combination of a modern variant of the LZ77 algorithm, Huffman
coding and 2nd order context modeling, with a compression ratio comparable
to the best currently available general-purpose compression methods.
It is similar in speed with deflate but offers more dense compression.
This package installs a Python 3 module.


%package -n %{name}-devel
Summary:        Lossless compression algorithm (development files)
Requires: %{name}%{?_isa} = %{version}-%{release} 

%description -n %{name}-devel
Brotli is a generic-purpose lossless compression algorithm that compresses
data using a combination of a modern variant of the LZ77 algorithm, Huffman
coding and 2nd order context modeling, with a compression ratio comparable
to the best currently available general-purpose compression methods.
It is similar in speed with deflate but offers more dense compression.
This package installs the development files

%prep
%autosetup -n %{lastversion_dir}
# 1.0.8 tarball had no python bindings so we bring those from source files on PyPI
#unzip %{SOURCE2}
#mv -f Brotli-1.0.8/setup.* ./
#mv -f Brotli-1.0.8/python ./

# fix permissions for -debuginfo
# rpmlint will complain if I create an extra %%files section for
# -debuginfo for this so we'll put it here instead
%{__chmod} 644 c/enc/*.[ch]
%{__chmod} 644 c/include/brotli/*.h
%{__chmod} 644 c/tools/brotli.c

%build
mkdir -p build
cd build
%cmake .. -DCMAKE_INSTALL_PREFIX="%{_prefix}" \
    -DCMAKE_INSTALL_LIBDIR="%{_libdir}"
%make_build
cd ..
%if %{with python2}
%py2_build
%endif
%py3_build

%install
cd build
%make_install

# I couldn't find the option to not build the static libraries
%__rm "%{buildroot}%{_libdir}/"*.a

cd ..
# Must do the python2 install first because the scripts in /usr/bin are
# overwritten with every setup.py install, and in general we want the
# python3 version to be the default. If, however, we're installing separate
# executables for python2 and python3, the order needs to be reversed so
# the unversioned executable is the python2 one.
%if %{with python2}
%py2_install
%endif
%py3_install
%{__install} -dm755 "%{buildroot}%{_mandir}/man3"
cd docs
for i in *.3;do
%{__install} -m644 "$i" "%{buildroot}%{_mandir}/man3/${i}brotli"
done

%ldconfig_scriptlets

%check
cd build
#ctest -V
cd ..
%if %{with python2}
# tests fail in RHEL 6 due to smth :)
%if 0%{?rhel} >= 7
#%%{__python2} setup.py test
%endif
%endif
#%%{__python3} setup.py test

%files
%{_bindir}/brotli
%{_libdir}/*.so.*
# Virtually add license macro for EL6:
%{!?_licensedir:%global license %%doc}
%license LICENSE

# Note that there is no %%files section for the unversioned python module
# if we are building for several python runtimes
%if %{with python2}
%files -n python2-%{name}
%{python2_sitearch}/*
# Virtually add license macro for EL6:
%{!?_licensedir:%global license %%doc}
%license LICENSE
%endif

%files -n python%{python3_pkgversion}-%{name}
%{python3_sitearch}/*
# Virtually add license macro for EL6:
%{!?_licensedir:%global license %%doc}
%license LICENSE

%files -n %{name}-devel
%{_includedir}/*
%{_libdir}/*.so
%{_libdir}/pkgconfig/*
%{_mandir}/man3/*


%changelog
* Thu Aug 27 2020 Danila Vershinin <info@getpagespeed.com> 1.0.8-1
- release 1.0.8

* Wed Oct 24 2018 Danila Vershinin <info@getpagespeed.com> 1.0.7-1
- upstream version auto-updated to 1.0.7

* Thu Sep 20 2018 Danila Vershinin <info@getpagespeed.com> 1.0.6-1
- upstream version auto-updated to 1.0.6

* Wed Sep 5 2018 Danila Vershinin <info@getpagespeed.com> - 1.0.5-2
- update for EL6 and EL7 compatibility

* Fri Jul 13 2018 Travis Kendrick pouar@pouar.net> - 1.0.5-1
- update to 1.0.5

* Thu Jul 12 2018 Fedora Release Engineering <releng@fedoraproject.org> - 1.0.4-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_29_Mass_Rebuild

* Mon Jun 18 2018 Miro Hrončok <mhroncok@redhat.com> - 1.0.4-3
- Rebuilt for Python 3.7

* Wed Apr 18 2018 Travis Kendrick pouar@pouar.net> - 1.0.4-2
- update to 1.0.4

* Sat Mar 03 2018 Travis Kendrick <pouar@pouar.net> - 1.0.3-1
- update to 1.0.3

* Wed Feb 07 2018 Fedora Release Engineering <releng@fedoraproject.org> - 1.0.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Sat Feb 03 2018 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 1.0.1-2
- Switch to %%ldconfig_scriptlets

* Fri Sep 22 2017 Travis Kendrick <pouar@pouar.net> - 1.0.1-1
- update to 1.0.1

* Wed Aug 02 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.6.0-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.6.0-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Tue May 23 2017 Travis Kendrick <pouar@pouar.net> - 0.6.0-4
- add man pages

* Sun May 14 2017 Travis Kendrick <pouar@pouar.net> - 0.6.0-3
- wrong directory for ctest
- LICENSE not needed in -devel
- fix "spurious-executable-perm"
- rpmbuild does the cleaning for us, so 'rm -rf %%{buildroot}' isn't needed

* Sat May 13 2017 Travis Kendrick <pouar@pouar.net> - 0.6.0-2
- include libraries and development files

* Sat May 06 2017 Travis Kendrick <pouar@pouar.net> - 0.6.0-1
- Initial build
