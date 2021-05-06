---

# Edit the frontmatter for all the homepage sections. To make edits to the about content, scroll down past the frontmatter and edit the markdown.

permalink: /
layout: homepage

# Hero
hero_image: 'img/hero_bg.png'
hero_title: 'MIQA'
hero_description: 'Efficient and accurate QC processing by leveraging modern UI/UX and deep learning techniques'
learn_more_link: 'https://github.com/OpenImaging/miqa'
github_link: 'https://github.com/OpenImaging/miqa'

# Resources
features_title: Features
resources_blurb: >-
  <p class="text-xs">Are you funded by the ECP/VTK-m project? See <a href="https://m.vtk.org/index.php/ECP/VTK-m_project_management" target="_blank">ECP/VTK-m project management</a>.</p>

features:
  - name: Multi-site
    icon: img/icons/MultiSite.png
    description: 'MIQA is cloud-based for distributed access by geographically distributed teams. All participants can securely view and annotate imagery from multiple sites.'
  - name: AI Powered
    icon: img/icons/AIPowered.png
    description: 'MIQA provides neural networks pre-trained for anomaly detection to ease the burden of distributed quality assurance testing. MIQA will learn from annotations entered by experts to further improve its AI predictions.'
  - name: Open Source
    icon: img/icons/OpenSource.png
    description: 'Open Source means MIQA can be extended and modified for new applications. Join our growing team of developers and develop only the extra features you need.'
  - name: Modern UI/UX
    icon: img/icons/ModernUIUX.png
    description: 'MIQA uses new Javascript frameworks, including Vue.js, Vuetify, and Vuex to speed development and improve UI performance.'
  - name: Efficient Data Management and Caching
    icon: img/icons/DataManagement.png
    description: 'MIQA builds on Girder, a mature, open source enterprise data hosting platform with multi-threading and scaleable storage and caching options.'
  - name: Easy to Deploy
    icon: img/icons/Deploy.png
    description: 'Get started right away using our pre-built docker containers.'

resources:
  - name: Building VTK-m
    icon: ri-stack-fill
    link: 'https://gitlab.kitware.com/vtk/vtk-m/blob/master/README.md#building'
  - name: Software Dependencies
    icon: ri-terminal-box-fill
    link: 'https://gitlab.kitware.com/vtk/vtk-m/blob/master/README.md#dependencies'
  - name: Contributing
    icon: ri-chat-check-fill
    link: 'https://gitlab.kitware.com/vtk/vtk-m/blob/master/CONTRIBUTING.md'
  - name: Mailing List
    icon: ri-send-plane-fill
    link: 'http://vtk.org/mailman/listinfo/vtkm'
  - name: User Guide
    icon: ri-book-2-fill
    link: 'https://gitlab.kitware.com/vtk/vtk-m-user-guide/-/wikis/home'
  - name: Doxygen Documentation
    icon: ri-booklet-fill
    link: 'http://m.vtk.org/documentation/'
  - name: Tutorial
    icon: ri-lightbulb-flash-fill
    link: '/tutorial'
  - name: VTK-m Assets
    icon: ri-angularjs-fill
    link: '/assets'

# Publications
publications: true
pubs_title: VTK-m Publications
pubs_blurb: >-
  <p>Please use the first paper when referencing VTK-m in scientific publications.</p>

---

# **M**edical **I**mage **Q**uality **A**ssurance **(MIQA)**

MIQA is designed for medical imaging QA/QC from the ground up, enabling workflows that not only reflect the specific requirements of distributed medical imaging studies, but also minimize the time spent on labor-intensive operations, such as visually reviewing scans.
