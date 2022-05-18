Specific instructions including commands can be found in [prod/README.md](prod/README.md). Those instructions will offer a step-by-step guide for commands to run for configuration. This guide is preparatory material for those instructions, which assume you already have some prerequisite components and server experience. Below are some explanations of these prerequisites, which you may need to spend some time to understand and obtain from your organization before you can get started with the production instructions.

### Server machine preparation

One prerequisite to setting up a MIQA instance is a server machine. The commands we supply will be for Linux-based systems. Each organization may have different regulations and processes for obtaining access to a virtual machine that can communicate within the organization. This is the recommended approach to protect the information the database will contain. There are other ways to obtain access to a virtual machine, such as cloud deployment platforms like Amazon Web Services or Microsoft Azure. Whatever approach is taken, this tutorial will assume that the administrator has `sudo` access on some Linux-based machine with connectivity capabilities.



Once you have obtained a server, you can choose a domain name that is appropriate for that machine and which communicates that this domain holds the MIQA instance for your organization. Your choice of domain name will affect the steps of your configuration process, as there are several places in the configuration instructions where the domain name should be inserted. Changing your domain name is not impossible, but will require reconfiguration, so choose something you are comfortable keeping.

### Docker compose

The MIQA system has many component services that work together to offer a complex system. As such, MIQA is set up to utilize `docker-compose` to manage these services in an efficient, containerized, and easy to use manner. Docker is therefore a prerequisite for simple setup.



Some helpful hints for using docker-compose:

-   Avoid using the `docker-compose down` command to undo a `docker-compose up` command. Instead, use `docker-compose stop` when necessary. The `up` command equates to a “build and deploy” mode and the `down` command equates to “stop deployment and unbuild”, which will destroy the database container resulting in loss of any data present. Contrastively, the `stop` command equates to just “stop the deployment”.


### Mail server

MIQA has an email feature that allows users to send screenshots of scan slices to colleagues. As such, the MIQA server needs a specialized mail server to send those emails. There are many options for free open source mail servers for enterprise or personal use. Our documentation (see [production instructions](prod/README.md)) recommends Mailtrap, which only requires an account for their online portal . If your organization has some other standard for mail servers, that option is equally compatible with MIQA. You simply need to obtain the values for `host`, `port`, `user`, and `password` for the mail server you choose. The production instructions will specify how to use these values in the configuration.

### SSL certificates

For any server to offer secure communication via HTTPS, the server machine needs to have valid certificate files signed by a third party certificate authority. Just like virtual machine allocation, each organization may have different procedures for obtaining signed SSL certificates, so it is recommended to contact the system administration for your organization. In the case that you are setting up a test instance that does not need reliable certificates, a self-signed certificate may be sufficient. The production instructions provide the steps to create or place the certificate files in the correct location.
