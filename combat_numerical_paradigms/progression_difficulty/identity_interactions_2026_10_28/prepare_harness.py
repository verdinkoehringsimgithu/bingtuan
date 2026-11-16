from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'compound_runtime_2026_10_28/CompoundParityHarness.cs').read_text(encoding='utf-8')
s=s.replace('CompoundParityHarness','InteractionParityHarness')
s=s.replace('public ExpectedCompoundAction[] actions;', '''public ExpectedCompoundAction[] actions;
    public Dictionary<string,object> leftEvasionSummary,rightEvasionSummary,leftSupportSummary,rightSupportSummary,leftAmplificationSummary,rightAmplificationSummary,leftAugmentationSummary,rightAugmentationSummary,leftTacticalSummary,rightTacticalSummary;''')
index=s.index('    public static void Main(')
s=s[:index]+'''    private static void Partial(object actual,object expected,string path)
    {
        var expectedMap=expected as Dictionary<string,object>;
        if(expectedMap!=null)
        {
            var actualMap=(Dictionary<string,object>)actual;
            foreach(var p in expectedMap){if(!actualMap.ContainsKey(p.Key))throw new Exception(path+" missing "+p.Key);Partial(actualMap[p.Key],p.Value,path+"."+p.Key);}return;
        }
        if(expected==null){if(actual!=null)throw new Exception(path+" expected null");return;}
        var array=expected as System.Collections.IList;
        if(array!=null)
        {
            var values=(System.Collections.IList)actual;if(values.Count!=array.Count)throw new Exception(path+" array length");
            for(int k=0;k<array.Count;k++)Partial(values[k],array[k],path+"["+k+"]");return;
        }
        if(expected is string||expected is bool){if(!expected.Equals(actual))throw new Exception(path+" scalar");return;}
        Near(Convert.ToDouble(actual),Convert.ToDouble(expected),path);
    }
    private static void State(object actual,object expected,string name)
    {
        var json=new JavaScriptSerializer {MaxJsonLength=int.MaxValue,RecursionLimit=1000};Partial(json.DeserializeObject(json.Serialize(actual)),expected,name);
    }
'''+s[index:]
anchor='draws+=index;actions+=actionIndex;'
s=s.replace(anchor,'''State(a.EvasionBonds.Snapshot(),c.leftEvasionSummary,c.name+" evasion");State(b.EvasionBonds.Snapshot(),c.rightEvasionSummary,c.name+" enemy evasion");
            State(a.SupportBonds.Snapshot(),c.leftSupportSummary,c.name+" support");State(b.SupportBonds.Snapshot(),c.rightSupportSummary,c.name+" enemy support");
            State(a.AmplificationBonds.Snapshot(),c.leftAmplificationSummary,c.name+" amplification");State(b.AmplificationBonds.Snapshot(),c.rightAmplificationSummary,c.name+" enemy amplification");
            State(a.AugmentationBonds.Snapshot(),c.leftAugmentationSummary,c.name+" augmentation");State(b.AugmentationBonds.Snapshot(),c.rightAugmentationSummary,c.name+" enemy augmentation");
            State(a.TacticalBonds.Snapshot(),c.leftTacticalSummary,c.name+" tactical");State(b.TacticalBonds.Snapshot(),c.rightTacticalSummary,c.name+" enemy tactical");
            '''+anchor)
(HERE/'InteractionParityHarness.cs').write_text(s,encoding='utf-8')
