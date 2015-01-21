# ./inventory.mc
inventory do
  format "%s,%s,%s,%s,%s,%s,%s,%s"
  fields { [ identity, facts["hostname"], facts["ipaddress"], facts["cf_domain"], facts["cf_uaa_urislogin"], facts["cf_uaa_urisuaa"], facts["fqdn"], facts["operatingsystemrelease"] ] }
end