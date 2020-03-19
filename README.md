Filewall SMTPD
===================

#### Warning: This is beta software and is not intended for use in a production environment.
  
This is an SMTP forwarding server that receives email, sends any attachments through  [Filewall.io](https://filewall.io) for processing, and sends the filtered email to another SMTPD.

This allows you to use [Filewall.io](https://filewall.io) as a content filter with any mail server. 

Instructions for setting up Postfix are provided below.

## Setting up the SMTP server

### Install using Python pip
```
$ sudo pip install git+https://github.com/filewallio/filewall-smtpd
```
### Authorize the API

Set the API key in ```/etc/filewall-smtpd.conf``` 

**Note:** Use our [API documentation](https://filewall.io/docs/api/overview) to obtain an API key.

### Start the service

```
$ service filewall-smtpd start
```
To start on boot, use: 

```
systemctl enable filewall-smtpd.service
```

## Setting up Postfix

Use the following quick configuration steps to make Postfix redirect all emails through the Filewall SMTPD.

For more details, see the [Postfix Advanced Content Filtering documentation](http://www.postfix.org/FILTER_README.html). 

### (/etc/postfix/)main.cf:
```
content_filter = scan:localhost:10025
receive_override_options = no_address_mappings
```

### (/etc/postfix/)master.cf:
```
scan      unix  -       -       n       -       10      smtp
      -o smtp_send_xforward_command=yes
      -o disable_mime_output_conversion=yes

localhost:10026 inet  n       -       n       -       10      smtpd
      -o content_filter=
      -o receive_override_options=no_unknown_recipient_checks,no_header_body_checks,no_milters
      -o smtpd_authorized_xforward_hosts=127.0.0.0/8
```

