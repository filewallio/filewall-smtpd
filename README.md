Filewall SMTPD
===================

#### Warning: This is beta software and is not intended for use in a production environment.
  
This is an SMTP forwarding server that receives email, sends any attachments through  [Filewall.io](https://filewall.io)  for processing, and sends the filtered email to another SMTPD.

This enables you to use [Filewall.io](https://filewall.io) as a content filter for your favourite mailserver. 
An example for Postfix is provided below.

## Setting up the SMTP server

### Install with python pip
```
$ sudo pip install git+https://github.com/filewallio/filewall-smtpd
```

Set the API key in ```/etc/filewall-smtpd.conf``` 
<!--- 

Does this relate at all to obtaining an API key using a filewall account as described in the API docs? 
-- Yep, thats the api key
--->

### Start the service

```
$ service filewall-smtpd start
```
To start on boot, use 

```
systemctl enable filewall-smtpd.service
```

## Setting up Postfix


Use the following quick configuration steps so Postfix will redirect all emails through filewall-smtpd.

For more details, check the Postfix Advanced Content Filtering [Readme](http://www.postfix.org/FILTER_README.html) 

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


<!--- Do these work for everyone? If not, don't have it here. 
We want it to be generic enough that anyone can follow with minor modifications

-- Yep, if they won't work because your mailserver configuration is something special, you will know about that and figure it out.

--->
