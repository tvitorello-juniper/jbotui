# CENTOS 7 Base Image, no other linux distros are supported
FROM centos:7

# Update YUM repo
RUN yum -y update

# Install deltarpm
RUN yum -y install deltarpm

# Add EPEL repo
RUN yum -y install epel-release-7
RUN rpm --import http://download.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-7

# Create TEMP folder
RUN mkdir /TEMP/

# Copy dependencies and requirements files
COPY requirements.txt /TEMP/requirements.txt
COPY dependencies.txt /TEMP/dependencies.txt

# Install YUM depedencies
RUN yum -y install $(cat /TEMP/dependencies.txt)
RUN yum -y group install "Development Tools"

# Upgrade PIP and setuptools
RUN pip install --upgrade pip
RUN yum upgrade python-setuptools

# Install PIP depedencies 
RUN pip install -r TEMP/requirements.txt

# Install JSNAP rpm
COPY jsnap-1.0-5.x86_64.rpm /TEMP/jsnap.rpm
RUN rpm -Uvh /TEMP/jsnap.rpm

# Expose ports
EXPOSE 80
EXPOSE 443
EXPOSE 8000
EXPOSE 8080
EXPOSE 8081
EXPOSE 8082
EXPOSE 8443

# Create apache SSL settings folder
RUN mkdir /etc/httpd/ssl

# Configure cert

# Create non-root user
RUN adduser juniper
RUN chown -R juniper etc/httpd/ssl
RUN chmod -R u+w etc/httpd/ssl

# Create project folder and copy project
RUN mkdir /jbotserv/
COPY nginx.conf /etc/nginx/sites-enabled/
WORKDIR /jbotserv/
COPY jbotserv /jbotserv
COPY entrypoint.sh entrypoint.sh
COPY generate_certificate.exp generate_certificate.exp
COPY djan.ini djan.ini


# Configure permissions for project folder
RUN chown -R juniper . && chmod -R u+wx .

RUN groupadd www-serv

# Configure Django
RUN python manage.py makemigrations
RUN python manage.py migrate
RUN python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('juniper', 'juniper@example.com', 'juniper123')"
RUN python manage.py collectstatic --noinput
ENV PATH="/usr/jawa/bin:${PATH}"
# Entrypoint
ENTRYPOINT ./entrypoint.sh
