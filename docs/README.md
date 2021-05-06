# vtkm-web
This repository is home to the files for the VTK-m website. Below you will find building and deployment instructions as well as documentation for plugins and packages that this website depends on.

Our Netlify build is live at https://vtk-m.vtk.org (this is a temporary domain and will be pointed to https://m.vtk.org when our work is done).

**Note:** This site will not build on GitHub pages. It can be optimized to do so, however the "jekyll-scholar" plugin does not work on GitHub Pages, so we opted for deploying on Netlify.

## Developing locally
Start by cloning this repository followed by `cd vtkm-web`.

#### Building Tailwind
Tailwind and our other dev packages need to be built prior to Jekyll, as it needs the `manifest.yml` file to link to the properly built CSS.

1. Open a new tab in your shell application
2. Install dev dependencies - `npm install`
3. Run one of the build commands:
    - To build for development run `npm run dev`
    - To build for production run `npm run prod`
    - If you are making a lot of changes, you might want to watch for changes using `npm run watch`

#### Setting up Jekyll
1. Install gem dependencies using bundler - `bundle install` (if you don't have bundler installed, you may need to run `gem install bundler`)
    - You may need to update the bundler gems. If so, run `bundle update`.
3. Serve the site using `bundle exec jekyll serve`, or build using `bundle exec jekyll build`

#### Other things to note
- All pages (including index) will be found in the `_pages` directory. `permalink: /page_name` is required on all pages.

## Deploying this site
We are using Netlify to deploy the site. Committing and pushing your changes should be all that is needed to deploy.

If you should need to set this up again, refer to https://www.netlify.com/blog/2020/04/02/a-step-by-step-guide-jekyll-4.0-on-netlify/#connecting-to-netlify

----

## Documentation and resources

### Jekyll Scholar
This website utilizes the [Jekyll Scholar plugin](https://github.com/inukshuk/jekyll-scholar) to parse bibliography files.

### Icons
We are using [Remix Icon](https://remixicon.com/) to handle all iconography on the website. Add something like `<i class="ri-pencil-fill"></i>` to use an icon.

### Tailwind CSS
This website utilizes [TailwindCSS](https://tailwindcss.com/docs) as a CSS framework. The benefit is that it gives you access to the full palette of CSS attributes as clases without writing any CSS.

**We've extended our configuration of Tailwind CSS in the following ways:**
1. Support for primary, secondary and accent color classes, ie. `bg-primary-500` or `text-accent-700`
2. Support for 2 smaller font size classes, `text-2xs` and `text-3xs`
3. Support for 2 smaller min-width/max-width sizes, ie. `max-w-2xs` or `min-w-3xs`
4. Added [plugin](https://www.npmjs.com/package/tailwindcss-textshadow) to support `text-shadow` classes
    - Extended the plugin's classes to include `text-shadow-2xl` for a larger shadow.

**We've also added NON-Tailwind helper classes to improve the overall Tailwind experience.**
1. Content - We've added a `.content` class to a wrapper of the content for the purpose of adding styles to `<ul>`'s, `<ol>`'s and `<p>`'s (since Tailwind strips those bare).
    - Please note, that the elements listed above that are outside of `<main class="content">` will not have those styles.
3. Buttons - use the class `button` on any `<a>`
    - Append these classes for different types of buttons
        - `is-sm` - Small button
        - `is-xs` - Extra small button
        - `is-shadowed` - Adds drop shadow to button
        - `is-primary` - Button will use the primary color set in the Tailwind config
        - `is-secondary` - Button will use the secondary color set in the Tailwind config
        - `is-accent` - Button will use the accent color set in the Tailwind config
        - `is-outline` - Will make an outlined button
4. Bibliography - The jekyll-scholar plugin addes an `<ol>` with a class of `bibliography`. The bibliography class has been added to the CSS to add some simple styles
