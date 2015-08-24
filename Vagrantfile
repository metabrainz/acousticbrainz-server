# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

NCPUS = ENV['AB_NCPUS'] || '1'
MEM = ENV['AB_MEM'] || '1024'
MIRROR = ENV['AB_MIRROR'] || 'archive.ubuntu.com'
NOHL = ENV['AB_NOHL'] || false

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "ubuntu/trusty64"
  config.vm.hostname = "acousticbrainz-server"

  config.vm.provider "virtualbox" do |v|
    # Need more resources to be able to compile Essentia with related libs
    v.memory = MEM.to_i
    v.cpus = NCPUS.to_i
  end

  # Use a custom vm name
  config.vm.define :acousticbrainz do |t|
  end

  bootstrap_args = []
  if !NOHL
    bootstrap_args.push("-h")
  end
  bootstrap_args.push(MIRROR)

  config.vm.provision :shell, path: "admin/bootstrap.sh", args: bootstrap_args
  config.vm.provision :shell, path: "admin/setup_app.sh", args: "/home/vagrant/acousticbrainz-server", privileged: false

  config.vm.synced_folder ".", "/home/vagrant/acousticbrainz-server"

  # Web server forwarding:
  config.vm.network "forwarded_port", guest: 8080, host: 8080

  # PostgreSQL forwarding:
  config.vm.network "forwarded_port", guest: 5432, host: 15432

  # Create a private network, which allows host-only access to the machine
  # using a specific IP.
  config.vm.network "private_network", ip: "192.168.33.10"
end
