Filewall.io postfix filter
===================

This is Python code to achieve Advanced Content Filtering in Postfix
( http://www.postfix.org/FILTER_README.html ) with filewall.io . This Python code listens on one port to get emails from Postfix,
then .. does its magic..  and then re-inject the mail into Postfix. 

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
