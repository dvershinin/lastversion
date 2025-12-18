%global upstream_github mozilla
%global upstream_name mozjpeg
%global lastversion_tag x
%global lastversion_dir x

Name:           libmozjpeg
Version:        3.3.1
Release:        5%{?dist}
Summary:        MozJPEG, the improved JPEG encoder. Drop-in library

# Disable automatic .so provides like 'libjpeg.so.62(LIBJPEGTURBO_6.2)(64bit)'
# so that this package is not installed by accident by dependent programs
# this package must be explicitly installed by a user
AutoReqProv:    no

License:        BSD
URL:            https://github.com/%{upstream_github}/%{name}
Source0:        %{url}/archive/%{lastversion_tag}/%{name}-%{lastversion_tag}.tar.gz

BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  libtool

%ifarch %{ix86} x86_64
BuildRequires:  nasm
%endif

%description
%{name} reduces file sizes of JPEG images while retaining quality and
compatibility with the vast majority of the world's deployed decoders.

%{name} is a JPEG image codec that uses SIMD instructions (MMX, SSE2,
NEON) to accelerate baseline JPEG compression and decompression on x86, x86-64,
and ARM systems.  On such systems, %{name} is generally 2-4x as fast as
libjpeg, all else being equal.  On other types of systems, %{name} can
still outperform libjpeg by a significant amount, by virtue of its
highly-optimized Huffman coding routines.  In many cases, the performance of
%{name} rivals that of proprietary high-speed JPEG codecs.

%{name} implements both the traditional libjpeg API as well as the less
powerful but more straightforward TurboJPEG API.  %{name} also features
colorspace extensions that allow it to compress from/decompress to 32-bit and
big-endian pixel buffers (RGBX, XBGR, etc.), as well as a full-featured Java
interface.

%{name} was forked from libjpeg-turbo.


%package utils
Summary:        Utilities for manipulating JPEG images
Requires:       %{name}%{?_isa} = %{version}-%{release}


%description utils
The %{name}-utils package contains simple client programs for accessing
the libjpeg functions. It contains cjpeg, djpeg, jpegtran, rdjpgcom and
wrjpgcom (with "moz" prefix, e.g. mozcjpeg).
Cjpeg compresses an image file into JPEG format. Djpeg decompresses a
JPEG file into a regular image file. Jpegtran can perform various useful
transformations on JPEG files. Rdjpgcom displays any text comments included in a
JPEG file. Wrjpgcom inserts text comments into a JPEG file.


%package        devel
Summary:        Development files for %{name}
Requires:       %{name}%{?_isa} = %{version}-%{release}
AutoReqProv:    no


%description    devel
The %{name}-devel package contains libraries and header files for
developing applications that use %{name}.


%package        static
Summary:        Static libraries for %{name}
Requires:       %{name}-devel%{?_isa} = %{version}-%{release}


%description    static
The %{name}-static package contains static libraries for
developing applications that use %{name}.


%prep
%setup -q -n %{upstream_name}-%{version}
sed -i 's@27-Mar-1998@17-Mar-2018 MozJPEG, GetPageSpeed@' jversion.h


%build
autoreconf -fiv
#%%configure --disable-static
%configure --libdir=%{_libdir}/%{name} \
  --includedir=%{_includedir}/%{name} --prefix=%{_prefix} \
  --program-prefix=moz
make %{?_smp_mflags}


%install
rm -rf %{buildroot}
%make_install docdir=%{_pkgdocdir} exampledir=%{_pkgdocdir}
find %{buildroot} -name '*.la' -exec rm -f {} ';'
# the magic:
mkdir -p ${RPM_BUILD_ROOT}%{_sysconfdir}/ld.so.conf.d
echo "%{_libdir}/%{name}" > %{buildroot}%{_sysconfdir}/ld.so.conf.d/%{name}-%{_arch}.conf

# Fix perms
chmod -x README-turbo.txt


%check
#make test


%post
/sbin/ldconfig
# New install
if [ $1 -eq 1 ]; then
    # print site info
    cat <<BANNER
----------------------------------------------------------------------

This premium package was brought to you by GetPageSpeed.com.

Please keep your existing subscription active for continued use:
* https://www.getpagespeed.com/repo-subscribe

Find out more about the GetPageSpeed repository at:
* https://www.getpagespeed.com/redhat

----------------------------------------------------------------------
BANNER
fi


%postun -p /sbin/ldconfig


%files
%doc README.md *.txt LICENSE.md README.ijg example.c
%{_libdir}/%{name}/libjpeg.so.62*
%{_libdir}/%{name}/libturbojpeg.so.*
%config(noreplace) %{_sysconfdir}/ld.so.conf.d/%{name}-%{_arch}.conf


%files static
%{_libdir}/%{name}/libjpeg.a
%{_libdir}/%{name}/libturbojpeg.a


%files devel
%doc coderules.txt jconfig.txt libjpeg.txt structure.txt example.c
%{_includedir}/%{name}/jconfig.h
%{_includedir}/%{name}/jerror.h
%{_includedir}/%{name}/jmorecfg.h
%{_includedir}/%{name}/jpeglib.h
%{_includedir}/%{name}/turbojpeg.h
%{_libdir}/%{name}/libjpeg.so
%{_libdir}/%{name}/libturbojpeg.so
%{_libdir}/%{name}/pkgconfig/libjpeg.pc
%{_libdir}/%{name}/pkgconfig/libturbojpeg.pc


%files utils
%doc usage.txt wizard.txt
%{_bindir}/mozcjpeg
%{_bindir}/mozdjpeg
%{_bindir}/mozjpegtran
%{_bindir}/mozrdjpgcom
%{_bindir}/mozwrjpgcom
%{_bindir}/moztjbench
%{_mandir}/man1/mozcjpeg.1*
%{_mandir}/man1/mozdjpeg.1*
%{_mandir}/man1/mozjpegtran.1*
%{_mandir}/man1/mozrdjpgcom.1*
%{_mandir}/man1/mozwrjpgcom.1*


%changelog
* Thu Mar 05 2020 Danila Vershinin <info@getpagespeed.com> - 3.3.1-4
- Drop-in library

* Sun Mar 10 2019 Danila Vershinin <info@getpagespeed.com> - 3.3.1-1
- Rebuild for 3.3.1

* Fri Oct 17 2014 Rahul Sundaram <sundaram@fedoraproject.org> - 2.1-1
- initial spec
