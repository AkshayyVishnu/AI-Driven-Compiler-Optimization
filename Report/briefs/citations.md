# DeepCompile - Citation Verification

Method: fetched arXiv abs pages / publisher pages with WebFetch; a few items confirmed only via WebSearch result snippets (marked "search"). docs.md was not read (literature_survey.md was).
Verified 2026-10-31.

## A. Literature survey (LS) candidates

| LS# | Claim in survey | Verified finding | Status |
|---|---|---|---|
| 1 | Wang & O'Boyle, Proc. IEEE 2018 | Authors correct (Zheng Wang, Michael O'Boyle). arXiv says "accepted to Proc. IEEE"; IEEE Xplore/DOI page returned no content, so volume/pages (106(11):1879-1901) NOT confirmed by me | VERIFIED (title/authors/year); vol/pages unconfirmed |
| 2 | Li et al., TPDS 2021 | Author list in survey is WRONG/truncated: real list has 10 authors (adds Lin Gan, Guangwen Yang). TPDS vol 32 no 3 pp 708-727 confirmed | VERIFIED (fix authors) |
| 3 | AutoTVM, "OSDI / NeurIPS" 2018 | Venue is NeurIPS 2018 (arXiv comment). Not OSDI. Authors correct | VERIFIED (fix venue) |
| 4 | Ansor, OSDI 2020 | Authors and venue correct | VERIFIED |
| 5 | MLGO "Google Research Team", 2020-21 | Real: Trofin, Qian, Brevdo, Lin, Choromanski, Li; title "MLGO: a Machine Learning Guided Compiler Optimizations Framework"; arXiv 2021 (2101.04808), no peer-reviewed venue on page | VERIFIED (fix authors/year/title) |
| 6 | Cummins et al., IEEE TC 2020 "Static Neural Compiler Optimization via DRL" | WRONG attribution. Real authors: Rahim Mammadli, Ali Jannesari, Felix Wolf; arXiv 2008.08951, 2020. The IEEE TC DOI in the survey was not confirmed and should be dropped (a workshop/arXiv paper is all I could confirm) | VERIFIED (fix authors; drop DOI/venue) |
| 7 | PolyGym "Multiple Contributors" | Real: Brauckmann, Goens, Castrillon, "PolyGym: Polyhedral Optimizations as an Environment for Reinforcement Learning", PACT 2021 (arXiv title differs: "A Reinforcement Learning Environment for Polyhedral Optimizations", 2104.13732). PACT pages 17-29 / DOI 10.1109/PACT52795.2021.00009 come from search results only | VERIFIED (authors, arXiv); PACT details via search |
| 8 | Quantum RL "Presented at DAC 2023" | Real: Nils Quetschlich, Lukas Burgholzer, Robert Wille, DAC 2023 | VERIFIED |
| 9 | Graphiler MLSys 2022 | Correct (Xie, Wang, Ye, Zhang, Fan; MLSys 4, 2022) | VERIFIED |
| 10 | NACOS "arXiv 2022" | Not found as a 2022 paper. "NACOS" appears only as a term in a 2024 survey by Bachiri et al. (arXiv 2408.04116). The survey's description (joint NAS+compiler search, 15-25% latency numbers) could not be tied to any real paper | UNVERIFIED - drop |
| 11 | oneDNN Graph Compiler, Intel, IEEE conf 2022 | Not searched successfully; no source opened | UNVERIFIED - drop |
| 12 | Souffle, 2021 | Real paper is ASPLOS 2024 (Xia, Zhao, Sun, Wang, Wen, Yu, Feng, Cui), not 2021. Survey's numbers (40-60% etc.) and "formal verification" claim are unsupported | VERIFIED as different paper/year (see key xia2024souffle); survey description UNVERIFIED |
| 13 | GNN pass order | No source found | UNVERIFIED - drop |
| 14 | PreTuner | No source found | UNVERIFIED - drop |
| 15 | Transferable Graph Optimizers | No source found (a real NeurIPS 2020 paper of this name exists in my memory but I did not open it) | UNVERIFIED - drop |

## B. Reference table (VERIFIED only, plus unverified at the end)

| key | authors | title | venue, year | URL opened | status |
|---|---|---|---|---|---|
| wang2018ml | Z. Wang, M. O'Boyle | Machine Learning in Compiler Optimisation | Proc. IEEE, 2018 (arXiv:1805.03441) | https://arxiv.org/abs/1805.03441 | VERIFIED |
| li2021dlc | M. Li, Y. Liu, X. Liu, Q. Sun, X. You, H. Yang, Z. Luan, L. Gan, G. Yang, D. Qian | The Deep Learning Compiler: A Comprehensive Survey | IEEE TPDS 32(3):708-727, 2021 | https://arxiv.org/abs/2002.03794 | VERIFIED |
| chen2018autotvm | T. Chen, L. Zheng, E. Yan, Z. Jiang, T. Moreau, L. Ceze, C. Guestrin, A. Krishnamurthy | Learning to Optimize Tensor Programs | NeurIPS 2018 | https://arxiv.org/abs/1805.08166 | VERIFIED |
| zheng2020ansor | L. Zheng, C. Jia, M. Sun, Z. Wu, C. H. Yu, A. Haj-Ali, Y. Wang, J. Yang, D. Zhuo, K. Sen, J. E. Gonzalez, I. Stoica | Ansor: Generating High-Performance Tensor Programs for Deep Learning | OSDI 2020 | https://arxiv.org/abs/2006.06762 | VERIFIED |
| trofin2021mlgo | M. Trofin, Y. Qian, E. Brevdo, Z. Lin, K. Choromanski, D. Li | MLGO: a Machine Learning Guided Compiler Optimizations Framework | arXiv:2101.04808, 2021 | https://arxiv.org/abs/2101.04808 | VERIFIED |
| mammadli2020static | R. Mammadli, A. Jannesari, F. Wolf | Static Neural Compiler Optimization via Deep Reinforcement Learning | arXiv:2008.08951, 2020 | https://arxiv.org/abs/2008.08951 | VERIFIED |
| brauckmann2021polygym | A. Brauckmann, A. Goens, J. Castrillon | A Reinforcement Learning Environment for Polyhedral Optimizations (PACT version titled "PolyGym: Polyhedral Optimizations as an Environment for Reinforcement Learning") | arXiv:2104.13732, 2021; PACT 2021 | https://arxiv.org/abs/2104.13732 | VERIFIED (arXiv); PACT via search |
| quetschlich2023quantum | N. Quetschlich, L. Burgholzer, R. Wille | Compiler Optimization for Quantum Computing Using Reinforcement Learning | DAC 2023 (arXiv:2212.04508) | https://arxiv.org/abs/2212.04508 | VERIFIED |
| xie2022graphiler | Z. Xie, M. Wang, Z. Ye, Z. Zhang, R. Fan | Graphiler: Optimizing Graph Neural Networks with Message Passing Data Flow Graph | MLSys 2022 | https://proceedings.mlsys.org/paper_files/paper/2022/hash/a1126573153ad7e9f44ba80e99316482-Abstract.html | VERIFIED |
| xia2024souffle | C. Xia, J. Zhao, Q. Sun, Z. Wang, Y. Wen, T. Yu, X. Feng, H. Cui | Optimizing Deep Learning Inference via Global Analysis and Tensor Expressions | ASPLOS 2024, pp. 286-301, DOI 10.1145/3617232.3624858 | https://eprints.whiterose.ac.uk/id/eprint/203681 | VERIFIED (repository record lists 7 authors; Teng Yu from search snippet, order per search) |
| cummins2024llmcompiler | C. Cummins, V. Seeker, D. Grubisic, B. Roziere, J. Gehring, G. Synnaeve, H. Leather | Meta Large Language Model Compiler: Foundation Models of Compiler Optimization | arXiv:2407.02524, 2024 | https://arxiv.org/abs/2407.02524 | VERIFIED |
| cummins2021compilergym | C. Cummins, B. Wasti, J. Guo, B. Cui, J. Ansel, S. Gomez, S. Jain, J. Liu, O. Teytaud, B. Steiner, Y. Tian, H. Leather | CompilerGym: Robust, Performant Compiler Optimization Environments for AI Research | arXiv:2109.08267, 2021 (CGO 2022 not confirmed) | https://arxiv.org/abs/2109.08267 | VERIFIED |
| cummins2020programl | C. Cummins, Z. V. Fisches, T. Ben-Nun, T. Hoefler, H. Leather | ProGraML: Graph-based Deep Learning for Program Optimization and Analysis | arXiv:2003.10536, 2020 | https://arxiv.org/abs/2003.10536 | VERIFIED |
| ullah2024llms | S. Ullah, M. Han, S. Pujar, H. Pearce, A. Coskun, G. Stringhini | LLMs Cannot Reliably Identify and Reason About Security Vulnerabilities (Yet?): A Comprehensive Evaluation, Framework, and Benchmarks | IEEE S&P 2024 (arXiv:2312.12575) | https://arxiv.org/abs/2312.12575 | VERIFIED |
| xia2023practical | C. S. Xia, Y. Wei, L. Zhang | Practical Program Repair in the Era of Large Pre-trained Language Models | ICSE 2023 (arXiv:2210.14179) | https://arxiv.org/abs/2210.14179 | VERIFIED |
| pearce2023zeroshot | H. Pearce, B. Tan, B. Ahmad, R. Karri, B. Dolan-Gavitt | Examining Zero-Shot Vulnerability Repair with Large Language Models | IEEE S&P 2023 (arXiv:2112.02125) | https://arxiv.org/abs/2112.02125 | VERIFIED |
| chen2021codex | M. Chen, J. Tworek, H. Jun, Q. Yuan, H. Ponde de Oliveira Pinto, et al. (58 authors) | Evaluating Large Language Models Trained on Code | arXiv:2107.03374, 2021 | https://arxiv.org/abs/2107.03374 | VERIFIED |
| wu2023autogen | Q. Wu, G. Bansal, J. Zhang, Y. Wu, B. Li, E. Zhu, L. Jiang, X. Zhang, S. Zhang, J. Liu, A. H. Awadallah, R. W. White, D. Burger, C. Wang | AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation | arXiv:2308.08155, 2023 | https://arxiv.org/abs/2308.08155 | VERIFIED |
| hong2023metagpt | S. Hong, M. Zhuge, J. Chen, X. Zheng, Y. Cheng, C. Zhang, J. Wang, Z. Wang, S. K. S. Yau, Z. Lin, L. Zhou, C. Ran, L. Xiao, C. Wu, J. Schmidhuber | MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework | arXiv:2308.00352, 2023 (ICLR 2024 not confirmed) | https://arxiv.org/abs/2308.00352 | VERIFIED |
| qian2024chatdev | C. Qian, W. Liu, H. Liu, N. Chen, Y. Dang, J. Li, C. Yang, W. Chen, Y. Su, X. Cong, J. Xu, D. Li, Z. Liu, M. Sun | ChatDev: Communicative Agents for Software Development | ACL 2024 (arXiv:2307.07924) | https://arxiv.org/abs/2307.07924 | VERIFIED |
| wei2022cot | J. Wei, X. Wang, D. Schuurmans, M. Bosma, B. Ichter, F. Xia, E. Chi, Q. Le, D. Zhou | Chain-of-Thought Prompting Elicits Reasoning in Large Language Models | arXiv:2201.11903, 2022 (NeurIPS 2022 not confirmed from page) | https://arxiv.org/abs/2201.11903 | VERIFIED |
| yang2011csmith | X. Yang, Y. Chen, E. Eide, J. Regehr | Finding and Understanding Bugs in C Compilers | PLDI 2011, pp. 283-294 | https://www.doi.org/10.1145/1993316.1993532 (ACM page 403; confirmed via search results incl. researchr/Utah preprint) | VERIFIED (search) |
| lopes2021alive2 | N. P. Lopes, J. Lee, C.-K. Hur, Z. Liu, J. Regehr | Alive2: Bounded Translation Validation for LLVM | PLDI 2021, pp. 65-79 | https://pldi21.sigplan.org/details/pldi-2021-papers/5/Alive2-Bounded-Translation-Validation-for-LLVM (via search; ACM 403) | VERIFIED (search) |
| mitre-cwe | MITRE Corporation (sponsor: DHS/CISA) | Common Weakness Enumeration (CWE) | online list | https://cwe.mitre.org/about/index.html | VERIFIED |
| sei-certc | Carnegie Mellon Univ. Software Engineering Institute (CERT) | SEI CERT C Coding Standard (2016 Edition) | online standard | https://cmu-sei.github.io/secure-coding-standards/sei-cert-c-coding-standard/ | VERIFIED |
| nacos (LS#10) | - | - | - | none | UNVERIFIED |
| onednn-graph (LS#11) | - | - | - | none | UNVERIFIED |
| gnn-passorder (LS#13) | - | - | - | none | UNVERIFIED |
| pretuner (LS#14) | - | - | - | none | UNVERIFIED |
| transferable-go (LS#15) | - | - | - | none | UNVERIFIED |

Note: the earlier brief's claim that LS#5 has wrong author/year and LS#6 is misattributed to Mammadli/Jannesari/Wolf is CONFIRMED. LS#7 and #8 authors resolved. LS#10-15 placeholders: only #12 maps to a real (different-year) paper; others unresolved. Also note arXiv-only items (MLGO, LLM Compiler, CompilerGym, ProGraML, AutoGen, MetaGPT, CoT, Codex) should be cited as preprints unless a venue is confirmed by the author.

## C. BibTeX (VERIFIED only)

```bibtex
@article{wang2018ml,
  author = {Wang, Zheng and O'Boyle, Michael},
  title = {Machine Learning in Compiler Optimisation},
  journal = {Proceedings of the IEEE},
  year = {2018},
  note = {arXiv:1805.03441}
}
@article{li2021dlc,
  author = {Li, Mingzhen and Liu, Yi and Liu, Xiaoyan and Sun, Qingxiao and You, Xin and Yang, Hailong and Luan, Zhongzhi and Gan, Lin and Yang, Guangwen and Qian, Depei},
  title = {The Deep Learning Compiler: A Comprehensive Survey},
  journal = {IEEE Transactions on Parallel and Distributed Systems},
  volume = {32}, number = {3}, pages = {708--727}, year = {2021}
}
@inproceedings{chen2018autotvm,
  author = {Chen, Tianqi and Zheng, Lianmin and Yan, Eddie and Jiang, Ziheng and Moreau, Thierry and Ceze, Luis and Guestrin, Carlos and Krishnamurthy, Arvind},
  title = {Learning to Optimize Tensor Programs},
  booktitle = {NeurIPS}, year = {2018}
}
@inproceedings{zheng2020ansor,
  author = {Zheng, Lianmin and Jia, Chengfan and Sun, Minmin and Wu, Zhao and Yu, Cody Hao and Haj-Ali, Ameer and Wang, Yida and Yang, Jun and Zhuo, Danyang and Sen, Koushik and Gonzalez, Joseph E. and Stoica, Ion},
  title = {Ansor: Generating High-Performance Tensor Programs for Deep Learning},
  booktitle = {OSDI}, year = {2020}
}
@misc{trofin2021mlgo,
  author = {Trofin, Mircea and Qian, Yundi and Brevdo, Eugene and Lin, Zinan and Choromanski, Krzysztof and Li, David},
  title = {{MLGO}: a Machine Learning Guided Compiler Optimizations Framework},
  year = {2021}, eprint = {2101.04808}, archivePrefix = {arXiv}
}
@misc{mammadli2020static,
  author = {Mammadli, Rahim and Jannesari, Ali and Wolf, Felix},
  title = {Static Neural Compiler Optimization via Deep Reinforcement Learning},
  year = {2020}, eprint = {2008.08951}, archivePrefix = {arXiv}
}
@misc{brauckmann2021polygym,
  author = {Brauckmann, Alexander and Goens, Andr{\'e}s and Castrillon, Jeronimo},
  title = {A Reinforcement Learning Environment for Polyhedral Optimizations},
  year = {2021}, eprint = {2104.13732}, archivePrefix = {arXiv}
}
@inproceedings{quetschlich2023quantum,
  author = {Quetschlich, Nils and Burgholzer, Lukas and Wille, Robert},
  title = {Compiler Optimization for Quantum Computing Using Reinforcement Learning},
  booktitle = {Design Automation Conference (DAC)}, year = {2023}
}
@inproceedings{xie2022graphiler,
  author = {Xie, Zhiqiang and Wang, Minjie and Ye, Zihao and Zhang, Zheng and Fan, Rui},
  title = {Graphiler: Optimizing Graph Neural Networks with Message Passing Data Flow Graph},
  booktitle = {Proceedings of Machine Learning and Systems (MLSys)}, volume = {4}, year = {2022}
}
@inproceedings{xia2024souffle,
  author = {Xia, Chunwei and Zhao, Jiacheng and Sun, Qianqi and Wang, Zheng and Wen, Yuan and Yu, Teng and Feng, Xiaobing and Cui, Huimin},
  title = {Optimizing Deep Learning Inference via Global Analysis and Tensor Expressions},
  booktitle = {ASPLOS}, pages = {286--301}, year = {2024}, doi = {10.1145/3617232.3624858}
}
@misc{cummins2024llmcompiler,
  author = {Cummins, Chris and Seeker, Volker and Grubisic, Dejan and Roziere, Baptiste and Gehring, Jonas and Synnaeve, Gabriel and Leather, Hugh},
  title = {Meta Large Language Model Compiler: Foundation Models of Compiler Optimization},
  year = {2024}, eprint = {2407.02524}, archivePrefix = {arXiv}
}
@misc{cummins2021compilergym,
  author = {Cummins, Chris and Wasti, Bram and Guo, Jiadong and Cui, Brandon and Ansel, Jason and Gomez, Sahir and Jain, Somya and Liu, Jia and Teytaud, Olivier and Steiner, Benoit and Tian, Yuandong and Leather, Hugh},
  title = {{CompilerGym}: Robust, Performant Compiler Optimization Environments for {AI} Research},
  year = {2021}, eprint = {2109.08267}, archivePrefix = {arXiv}
}
@misc{cummins2020programl,
  author = {Cummins, Chris and Fisches, Zacharias V. and Ben-Nun, Tal and Hoefler, Torsten and Leather, Hugh},
  title = {{ProGraML}: Graph-based Deep Learning for Program Optimization and Analysis},
  year = {2020}, eprint = {2003.10536}, archivePrefix = {arXiv}
}
@inproceedings{ullah2024llms,
  author = {Ullah, Saad and Han, Mingji and Pujar, Saurabh and Pearce, Hammond and Coskun, Ayse and Stringhini, Gianluca},
  title = {{LLMs} Cannot Reliably Identify and Reason About Security Vulnerabilities (Yet?): A Comprehensive Evaluation, Framework, and Benchmarks},
  booktitle = {IEEE Symposium on Security and Privacy}, year = {2024}
}
@inproceedings{xia2023practical,
  author = {Xia, Chunqiu Steven and Wei, Yuxiang and Zhang, Lingming},
  title = {Practical Program Repair in the Era of Large Pre-trained Language Models},
  booktitle = {ICSE}, year = {2023}
}
@inproceedings{pearce2023zeroshot,
  author = {Pearce, Hammond and Tan, Benjamin and Ahmad, Baleegh and Karri, Ramesh and Dolan-Gavitt, Brendan},
  title = {Examining Zero-Shot Vulnerability Repair with Large Language Models},
  booktitle = {IEEE Symposium on Security and Privacy}, year = {2023}
}
@misc{chen2021codex,
  author = {Chen, Mark and Tworek, Jerry and Jun, Heewoo and Yuan, Qiming and Ponde de Oliveira Pinto, Henrique and others},
  title = {Evaluating Large Language Models Trained on Code},
  year = {2021}, eprint = {2107.03374}, archivePrefix = {arXiv}
}
@misc{wu2023autogen,
  author = {Wu, Qingyun and Bansal, Gagan and Zhang, Jieyu and Wu, Yiran and Li, Beibin and Zhu, Erkang and Jiang, Li and Zhang, Xiaoyun and Zhang, Shaokun and Liu, Jiale and Awadallah, Ahmed Hassan and White, Ryen W. and Burger, Doug and Wang, Chi},
  title = {{AutoGen}: Enabling Next-Gen {LLM} Applications via Multi-Agent Conversation},
  year = {2023}, eprint = {2308.08155}, archivePrefix = {arXiv}
}
@misc{hong2023metagpt,
  author = {Hong, Sirui and Zhuge, Mingchen and Chen, Jiaqi and Zheng, Xiawu and Cheng, Yuheng and Zhang, Ceyao and Wang, Jinlin and Wang, Zili and Yau, Steven Ka Shing and Lin, Zijuan and Zhou, Liyang and Ran, Chenyu and Xiao, Lingfeng and Wu, Chenglin and Schmidhuber, J{\"u}rgen},
  title = {{MetaGPT}: Meta Programming for A Multi-Agent Collaborative Framework},
  year = {2023}, eprint = {2308.00352}, archivePrefix = {arXiv}
}
@inproceedings{qian2024chatdev,
  author = {Qian, Chen and Liu, Wei and Liu, Hongzhang and Chen, Nuo and Dang, Yufan and Li, Jiahao and Yang, Cheng and Chen, Weize and Su, Yusheng and Cong, Xin and Xu, Juyuan and Li, Dahai and Liu, Zhiyuan and Sun, Maosong},
  title = {{ChatDev}: Communicative Agents for Software Development},
  booktitle = {ACL}, year = {2024}
}
@misc{wei2022cot,
  author = {Wei, Jason and Wang, Xuezhi and Schuurmans, Dale and Bosma, Maarten and Ichter, Brian and Xia, Fei and Chi, Ed and Le, Quoc and Zhou, Denny},
  title = {Chain-of-Thought Prompting Elicits Reasoning in Large Language Models},
  year = {2022}, eprint = {2201.11903}, archivePrefix = {arXiv}
}
@inproceedings{yang2011csmith,
  author = {Yang, Xuejun and Chen, Yang and Eide, Eric and Regehr, John},
  title = {Finding and Understanding Bugs in {C} Compilers},
  booktitle = {PLDI}, pages = {283--294}, year = {2011}
}
@inproceedings{lopes2021alive2,
  author = {Lopes, Nuno P. and Lee, Juneyoung and Hur, Chung-Kil and Liu, Zhengyang and Regehr, John},
  title = {{Alive2}: Bounded Translation Validation for {LLVM}},
  booktitle = {PLDI}, pages = {65--79}, year = {2021}
}
@misc{mitre-cwe,
  author = {{MITRE Corporation}},
  title = {Common Weakness Enumeration ({CWE})},
  howpublished = {\url{https://cwe.mitre.org}}
}
@misc{sei-certc,
  author = {{Software Engineering Institute, Carnegie Mellon University}},
  title = {{SEI CERT C Coding Standard}},
  year = {2016},
  howpublished = {\url{https://cmu-sei.github.io/secure-coding-standards/sei-cert-c-coding-standard/}}
}
```
