%global commit 3ecd4d37e299289f81daebdacbc94f731935f5f8
%global commit_date 20210722
%global shortcommit %(c=%{commit}; echo ${c:0:7})

%global upstream_github gnachman
%global upstream_name iTerm2-shell-integration

Name:           iterm2-utilities
Version:        0
Release:        0.1.%{commit_date}git%{shortcommit}%{?dist}
Summary:        iTerm2 Shell Utilities
License:        GPLv2
URL:            https://iterm2.com/documentation-utilities.html
BuildArch:      noarch
Source0:        https://github.com/%{upstream_github}/%{upstream_name}/archive/%{commit}/%{upstream_name}-%{shortcommit}.tar.gz

%if 0%{?rhel} >= 8
# for pathfix.py
BuildRequires:  platform-python-devel
%endif

%description
Collection of shell scripts that help you take advantage of
some of unique features of iTerm2.


%prep
%autosetup -n %{upstream_name}-%{commit}
%if 0%{?rhel} >= 8
pathfix.py -pn -i %{__python3} utilities
%endif

%build
# nothing to do

%install
%{__mkdir_p} $RPM_BUILD_ROOT%{_bindir}
%{__install} -m755 utilities/* $RPM_BUILD_ROOT%{_bindir}


%files
%{!?_licensedir:%global license %%doc}
%license LICENSE
%{_bindir}/*


%changelog
* Fri May 28 2021 Danila Vershinin <info@getpagespeed.com> 0-0.1.20210528gitcd266fa
- Initial packaging
