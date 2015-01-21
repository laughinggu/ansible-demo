# ./inventory.mc
inventory do
  format "%s"
  fields { [ facts["ipaddress_eth0"] ] }
end