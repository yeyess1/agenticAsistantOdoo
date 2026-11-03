---
url: https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/15_final_word.html
title: 'Chapter 15: The final word'
fetched_at: '2026-11-03T00:50:51Z'
license: CC BY-SA 4.0
license_url: https://creativecommons.org/licenses/by-sa/4.0/
---

# Chapter 15: The final word {#chapter-15-the-final-word}

## Coding guidelines {#coding-guidelines}

We will start refactoring the code to match to the Odoo coding guidelines. The guidelines aim to improve the quality of the Odoo Apps code.

**Reference**: you will find the Odoo coding guidelines in Coding guidelines.

> Exercise
>
> Polish your code.
>
> Refactor your code to respect the coding guidelines. Don’t forget to run your linter and respect the module structure, the variable names, the method name convention, the model attribute order and the xml ids.

## Test on the runbot {#test-on-the-runbot}

Odoo has its own CI server named [runbot](https://runbot.odoo.com/). All commits, branches and PR will be tested to avoid regressions or breaking of the stable versions. All the runs that pass the tests are deployed on their own server with demo data.

> Exercise
>
> Play with the runbot.
>
> Feel free to go to the runbot website and open the last stable version of Odoo to check out all the available applications and functionalities.
