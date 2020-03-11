Filewall.io smptd
===================

#### ! This is BETA software, don't use it in production !
  
This is a forwarding smpt server. It receives mails on one port, sends any attachents through filewall.io, 
and sends a filtered mail to another smptd. 

It can be used to achieve Advanced Content Filtering with https://filewall.io in Postfix
( http://www.postfix.org/FILTER_README.html ) . 


###### Install service:
```
$ pip install git+https://github.com/filewallio/postfix-filter
$ filewall-smtpd installservice
```

Set your apikey in ```/etc/filewall-smtpd.conf```

###### Start Service
```
$ service filewall-smtpd start
```
To start filewall-smtpd  at boot time, use ```systemctl enable filewall-smtpd.service```.



###### Postfix
What you need to do on Postfix side is to edit configuration according to the suggestions made in the Advanced 
Content Filtering above, but for your convenience, here is the quick version that could work for you too:

###### (/etc/postfix/)main.cf:
```
content_filter = scan:localhost:10025
receive_override_options = no_address_mappings
```

###### (/etc/postfix/)master.cf:
```
scan      unix  -       -       n       -       10      smtp
      -o smtp_send_xforward_command=yes
      -o disable_mime_output_conversion=yes

localhost:10026 inet  n       -       n       -       10      smtpd
      -o content_filter=
      -o receive_override_options=no_unknown_recipient_checks,no_header_body_checks,no_milters
      -o smtpd_authorized_xforward_hosts=127.0.0.0/8
```


There are ways combinations of parameters to do that (see the FILTER_README referred above) but only this one 
worked for me. This is because what I needed is that mails come to my Python code BEFORE processed using 
virtual table and they get processed using virtual table AFTER. 
This is what I needed, but you can change the no_address_mappings parameter in main.cf and 
master.cf to do thy bidding.
