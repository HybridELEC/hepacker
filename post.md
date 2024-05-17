The project is at https://github.com/HybridELEC/hepacker , some of the images for devices I personally own are available at https://github.com/HybridELEC/HybridELEC

As long as you have a stock Android USB burning image for your amlogic-ng or amlogic-ne device then this should work. you just need that Android image, the latest CoreELEC upgrade tarball for the version of CE that verifies to work on your device, and the latest EmuELEC upgrade tarball for the version of EE that verifies to work on your device. Follow the project README and specify the DTB names and size of CE and EE storage paritions, and you should get a USB burning image. 

At this stage there won't be any data loss as long as you don't use the image. If you do use, note there's no "upgrade/partial install", there's only "full install": to erase your eMMC completely while installing. This is by-design: to both minimilize the space usage in system partition and fight against resellers that want to make cheap money with boxes with CE/EE pre-installed and other illegal stuffs pre-populated. As soon as you flash it you would lose all of your Android and possibly CoreELEC data on eMMC, and it's possible to brick you device if the flashing was interrupted. Be warned and be prepared.

This tool also only supports stock Android + official CE + official EE 3-in-1, it does not support Android + official CE (just do that with `ceemmc`) 2-in-1 or Android + official EE 2-in-1, or non-official CE/EE, this is also by-design.

The embedded CE and EE systems would report themselves as "official" because they're not touched in any means, the only thing hacked around is Android itself.

After burning you would get the stock Android experience as that's also not touched, you could use https://github.com/HybridELEC/HybridELEC_Rebooter (not pre-installed as I don't like pre-installed apps) to reboot into the on-eMMC CE or EE, as long as you have root permission, Android would function like your entrance: a cold boot would always get you into Android. Or you could use it just like a generic Android + CoreELEC box installed with ceemmc AFTER you boot an external CoreELEC installation once, in this case it's CE that functions as your entrance and you would need to manually reboot into Android.

If you have any problem, please open an issue on the project page, not here. Do note that as I developed the tool and all its depedencies (ampart, the partition tool to embed modified partition info; and ampack, the tool to unpack and repack the burning image) on Arch Linux, I don't support running them on any other Linux distro.

