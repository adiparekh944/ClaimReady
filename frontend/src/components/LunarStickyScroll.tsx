"use client"

import clsx from "clsx"

import { ScrollObserver } from "./ScrollObserver"

export default function Page() {
  const items = [
    {
        title: "Gather all your Images",
        content: "You must gather all of your images of your belongings in your home.",
    },
    {
      title: "Sort and Organize Image",
      content: "Before cataloging, you need to sort and organize all images by room or category to ensure nothing is overlooked.",
    },
    {
      title: "Catalog Every Belonging",
      content:
        "You must manually catalog each and every belonging by hand, which averages to 1500+.",
    },
    {
      title: "Obtain A Valuation",
      content:
        "After getting your belongings cataloged, you must scour the web and find prices for each item individually, taking well over 20+ hours.",
    },
    {
        title: "Verify and Cross-Check Data",
        content:
          "You will then need to verify each item’s valuation for accuracy and ensure no duplicate or missing entries exist to avoid claim rejections.",
    },
    {
        title: "CSV Consolidation",
        content:
          "You will then need to verify each item’s valuation for accuracy and ensure no duplicate or missing entries exist to avoid claim rejections.",
      },
  ]

  return (
    <div className="min-h-screen w-screen px-8 py-20 md:px-0">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <ScrollObserver className="relative grid grid-cols-2 gap-32">
          {(isHidden) => (
            <>
              <ScrollObserver.TriggerGroup className="py-[50vh] font-kumbh-sans">
                {items.map((item, index) => (
                  <ScrollObserver.Trigger id={`features-${index}`} key={index} className="relative scroll-mt-[50vh]">
                    {(isActive) => (
                      <div
                        className={clsx(
                          isActive ? "text-black" : "text-black/10 hover:text-black/30",
                          "relative -mx-8 -mb-4 rounded-2xl p-8 transition duration-300 hover:bg-white/10",
                        )}>
                        <div className="font-epilogue text-4xl font-bold">{item.title}</div>

                        <div className="mt-4 text-lg">{item.content}</div>

                        <a href={`#features-${index}`} className="absolute inset-0"></a>
                      </div>
                    )}
                  </ScrollObserver.Trigger>
                ))}
              </ScrollObserver.TriggerGroup>

              <div className="sticky top-0 h-[100vh]">
                <div className={clsx({ "opacity-0 delay-100": !isHidden }, "absolute inset-0 flex items-center")}>
                  <div className="aspect-square w-full rounded-3xl bg-white/10"></div>
                </div>

                <ScrollObserver.ReactorGroup className="flex items-center justify-center">
                  {items.map((item, index) => (
                    <ScrollObserver.Reactor key={index} id={`features-${index}`} className="absolute inset-0 flex items-center justify-center">
                      {(isActive) => (
                        <div
                          className={clsx(
                            {
                              "opacity-0 delay-100": !isActive,
                              "opacity-100": isActive,
                              "from-purple-100 to-indigo-300": index == 0,
                              "from-cyan-300 to-sky-400": index == 1,
                              "from-amber-300 to-orange-400": index == 2,
                            },
                            "aspect-square w-full rounded-3xl bg-gradient-to-b transition",
                          )}></div>
                      )}
                    </ScrollObserver.Reactor>
                  ))}
                </ScrollObserver.ReactorGroup>
              </div>
            </>
          )}
        </ScrollObserver>
      </div>
    </div>
  )
}
